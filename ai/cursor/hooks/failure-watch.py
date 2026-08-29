#!/usr/bin/env python3
"""Catch failed edits, silent command failures, and background crashes.

Observes Cursor hook events, records unresolved failures per conversation,
injects additional_context when the event supports it, and on `stop` sends a
follow-up if the agent ended while failures were still outstanding.

Soft / expected noise is filtered: curl -f HTTP 404/403/410 URL probes,
eza ``ls --icons`` alias misuse, and missing-file Delete/Read probes. A later
successful Shell can also resolve leftover soft Shell failures.

Always fail-open: invalid input or unexpected errors print `{}`.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Deliberately low: `from __future__ import annotations` makes the modern type
# syntax lazy, so the hook runs on any stock python3. A version bump in mise
# must never silently disable failure watching.
MIN_PY = (3, 9)

HOOK_DIR = Path.home() / ".cursor" / "hooks"
STATE_DIR = HOOK_DIR / "state" / "failure-watch"
LOG_PATH = HOOK_DIR / "logs" / "failure-watch.log"
FALLBACK_ROOT = Path(tempfile.gettempdir()) / "cursor-failure-watch"
MAX_EVENTS = 40
MAX_SUMMARY = 240
MAX_DETAIL = 800

EDIT_TOOLS = {
    "Write",
    "StrReplace",
    "Delete",
    "EditNotebook",
    "Edit",
    "TabWrite",
}
SKIP_TOOLS = {
    "Read",
    "Grep",
    "Glob",
    "LS",
    "XcodeLS",
    "XcodeGrep",
    "XcodeRead",
    "GetDynamicTools",
}

CRASH_RE = re.compile(
    r"segmentation fault|abort trap|bus error|illegal instruction|"
    r"trace/?bpt trap|trace trap|killed:\s*9|"
    r"fatal error|panic:|std::terminate|uncaught exception|"
    r"SIG(?:SEGV|ABRT|BUS|ILL|FPE|KILL|TRAP|SYS)|"
    r"Exception Type:\s+EXC_(?:CRASH|BAD_ACCESS)|"
    r"Process crashed|crash report",
    re.I,
)
EXIT_RE = re.compile(
    r"(?:exit[_ ]code|last_exit_code|exitCode)\s*[:=]\s*(-?\d+)",
    re.I,
)
PID_RE = re.compile(r"(?:^|\n)\s*pid:\s*(\d+)", re.I)
BG_RE = re.compile(
    r"command still running|running in background|has been backgrounded|"
    r"manually backgrounded|moved to background|output_file|"
    r"block_until_ms[\"']?\s*[:=]\s*0\b",
    re.I,
)
TERMINAL_FILE_RE = re.compile(r"(/[^\s\"']+/terminals/\d+\.txt)")
EXPECTED_NONZERO_RE = re.compile(
    r"(?:^|[;&|]\s*)(?:grep\b|egrep\b|fgrep\b|rg\b|ripgrep\b|"
    r"diff\b|cmp\b|test\b|\[\s|true\b|false\b|"
    r"git\s+(?:diff|status|grep)\b)",
    re.I,
)
OR_TRUE_RE = re.compile(r"\|\|\s*(?:true|:)\s*$")
# agent-shell-env.sh (preToolUse) prepends a ~700-char zsh anonymous function to
# every Shell command. Left in place it buries the real command past every clip
# and length check, so strip it before any classification.
ENV_PREFIX_RE = re.compile(r"\A\s*\(\)\s*\{.*?\n\}\s*;\s*", re.S)
# Cursor reports shell exit status in prose on the failure path, e.g.
# "Command failed with exit code 1"; EXIT_RE only matches key:value forms.
EXIT_TEXT_RE = re.compile(r"exit(?:ed with)?\s+(?:code|status)\s+(-?\d+)", re.I)
# Anything that still looks like a real error after known-benign patterns are
# removed. Used instead of a raw length threshold so that successful output from
# other commands in a chained invocation cannot defeat noise suppression.
ERROR_SIGNAL_RE = re.compile(
    r"\berror\b|\bfatal\b|\bpanic\b|traceback|exception|"
    r"command not found|no such file|not recognized|"
    r"permission denied|cannot |can't |could not|couldn't|"
    r"failed\b|refused|timed out|unauthorized|forbidden",
    re.I,
)
CURL_HTTP_MISS_RE = re.compile(
    r"curl:\s*\((?:22|56)\)\s*The requested URL returned error:\s*(404|403|410)\b",
    re.I,
)
EZA_ICONS_ARG_RE = re.compile(
    r"invalid value\s+'[^']*'\s+for\s+'--icons",
    re.I,
)
CURL_INVOCATION_RE = re.compile(r"(?:^|[\s;|&])curl\b([^\n]*)", re.I)
SIGNAL_NAMES = {
    129: "SIGHUP",
    132: "SIGILL",
    134: "SIGABRT",
    136: "SIGFPE",
    137: "SIGKILL",
    138: "SIGBUS",
    139: "SIGSEGV",
    142: "SIGXCPU",
    143: "SIGTERM",
}


def main() -> None:
    if sys.version_info < MIN_PY:
        log(
            "refusing Python %s (%s); need mise python %s+"
            % (
                sys.version.split()[0],
                sys.executable,
                ".".join(str(p) for p in MIN_PY),
            )
        )
        emit({})
        return
    raw = sys.stdin.read()
    if not raw.strip():
        emit({})
        return
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        emit({})
        return
    event = str(payload.get("hook_event_name") or "")
    try:
        out = dispatch(event, payload) or {}
    except Exception as exc:  # noqa: BLE001 — hooks must fail open
        log("hook error: %s" % exc)
        emit({})
        return
    emit(out)


def dispatch(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    conv = str(payload.get("conversation_id") or payload.get("session_id") or "_unknown")
    state = load_state(conv)
    state["conversation_id"] = conv
    if payload.get("generation_id"):
        state["generation_id"] = payload["generation_id"]

    if event == "postToolUseFailure":
        handle_tool_failure(state, payload)
        save_state(state)
        return {}
    if event == "postToolUse":
        ctx = handle_post_tool_use(state, payload)
        save_state(state)
        return {"additional_context": ctx} if ctx else {}
    if event == "afterShellExecution":
        ctx = handle_after_shell(state, payload)
        save_state(state)
        return {"additional_context": ctx} if ctx else {}
    if event == "afterFileEdit":
        handle_after_file_edit(state, payload)
        save_state(state)
        return {}
    if event == "subagentStop":
        handle_subagent_stop(state, payload)
        save_state(state)
        return {}
    if event == "sessionEnd":
        handle_session_end(state, payload)
        save_state(state)
        prune_old_state()
        return {}
    if event == "stop":
        return handle_stop(state, payload)
    return {}


def handle_tool_failure(state: dict[str, Any], payload: dict[str, Any]) -> None:
    if payload.get("is_interrupt"):
        return
    tool = str(payload.get("tool_name") or "unknown")
    if tool in SKIP_TOOLS:
        return
    err = str(payload.get("error_message") or "tool failed")
    if is_missing_file_probe(tool, err):
        return
    path = tool_path(payload.get("tool_input"))
    cmd = tool_command(payload.get("tool_input"))
    skip_reason = benign_shell_noise_reason(tool, err, cmd)
    exit_code = failure_exit_code(payload, err)
    if skip_reason or expected_nonzero(cmd, exit_code):
        return
    ftype = str(payload.get("failure_type") or "error")
    kind = "edit_failure" if tool in EDIT_TOOLS else "tool_failure"
    if ftype == "timeout":
        kind = "timeout"
    summary = "%s %s: %s" % (tool, ftype, clip(err, 160))
    record(
        state,
        kind=kind,
        summary=summary,
        detail=err,
        tool=tool,
        path=path,
        command=cmd,
        exit_code=exit_code,
        generation_id=payload.get("generation_id"),
    )


def failure_exit_code(payload: dict[str, Any], err: str) -> int | None:
    """Recover an exit code on the failure path, where the payload omits it."""
    for key in ("exit_code", "exitCode", "last_exit_code"):
        value = payload.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                pass
    m = EXIT_TEXT_RE.search(err or "")
    if m:
        return int(m.group(1))
    return extract_exit_code(None, err)


def is_missing_file_probe(tool: str, err: str) -> bool:
    if tool not in SKIP_TOOLS and tool not in {"Read", "Grep", "Glob", "LS", "Delete"}:
        return False
    lowered = (err or "").lower()
    return (
        "file not found" in lowered
        or "no such file" in lowered
        or "does not exist" in lowered
        or "couldn't find" in lowered
    )


def curl_uses_fail_flag(cmd: str) -> bool:
    """True when a curl invocation uses -f/--fail (incl. clustered -fsSL)."""
    for m in CURL_INVOCATION_RE.finditer(cmd or ""):
        args = m.group(1) or ""
        if re.search(r"(?:^|[\s])--fail(?:\s|=|$)", args):
            return True
        # short-opt clusters: -f, -fsSL, -sSfL, etc.
        if re.search(r"(?:^|[\s])-[A-Za-z]*f[A-Za-z]*(?:\s|=|$)", args):
            return True
    return False


def benign_shell_noise_reason(tool: str, err: str, cmd: str) -> str | None:
    """Return why a Shell tool_failure should not page the agent, else None."""
    if tool not in ("Shell", "AwaitShell"):
        return None
    err_s = err or ""
    cmd_s = cmd or ""
    # curl -f/--fail HTTP miss while probing alternate URLs is expected discovery noise.
    if CURL_HTTP_MISS_RE.search(err_s) and (
        curl_uses_fail_flag(cmd_s) or "curl" in cmd_s.lower() or not cmd_s.strip()
    ):
        # If the only hard error is curl HTTP miss (+ optional eza icons alias noise), skip.
        remainder = CURL_HTTP_MISS_RE.sub("", err_s)
        remainder = EZA_ICONS_ARG_RE.sub("", remainder)
        remainder = re.sub(
            r"error:\s*invalid value.*?(?:For more information, try '--help'\.)?",
            "",
            remainder,
            flags=re.I | re.S,
        )
        remainder = re.sub(r"\s+", " ", remainder).strip(" :-")
        if not ERROR_SIGNAL_RE.search(remainder):
            return "curl_http_miss_probe"
    # Bare eza --icons misuse from `ls` alias when a path was passed as icons value.
    if EZA_ICONS_ARG_RE.search(err_s):
        remainder = EZA_ICONS_ARG_RE.sub("", err_s)
        remainder = re.sub(
            r"error:\s*|\[possible values:[^\]]*\]|For more information, try '--help'\.?",
            "",
            remainder,
            flags=re.I,
        )
        remainder = re.sub(r"\s+", " ", remainder).strip(" :-")
        if not ERROR_SIGNAL_RE.search(remainder):
            return "eza_icons_alias_noise"
    return None


def is_soft_shell_failure(ev: dict[str, Any]) -> bool:
    if ev.get("kind") != "tool_failure" or ev.get("tool") not in ("Shell", "AwaitShell", None, ""):
        return False
    detail = str(ev.get("detail") or ev.get("summary") or "")
    cmd = str(ev.get("command") or "")
    return benign_shell_noise_reason("Shell", detail, cmd) is not None or bool(
        CURL_HTTP_MISS_RE.search(detail) or EZA_ICONS_ARG_RE.search(detail)
    )


def resolve_soft_shell_failures(state: dict[str, Any], cmd: str, text: str) -> int:
    """Mark recoverable Shell probe failures resolved after a successful shell step."""
    events = state.get("events") or []
    cleared = 0
    success_looks_related = bool(
        re.search(r"\bcurl\b|\bhelm\b|get\.helm\.sh|github\.com/.*/releases", (cmd or "") + "\n" + (text or ""), re.I)
    )
    for ev in events:
        if ev.get("notified") or ev.get("resolved"):
            continue
        if not is_soft_shell_failure(ev):
            continue
        # Always clear pure soft probes after any successful shell; prefer related cmds.
        if success_looks_related or benign_shell_noise_reason(
            "Shell", str(ev.get("detail") or ""), str(ev.get("command") or "")
        ):
            ev["resolved"] = True
            ev["notified"] = True
            cleared += 1
    return cleared


def handle_post_tool_use(state: dict[str, Any], payload: dict[str, Any]) -> str | None:
    tool = str(payload.get("tool_name") or "")
    if tool in SKIP_TOOLS:
        return None
    output = parse_maybe_json(payload.get("tool_output"))
    text = stringify(payload.get("tool_output"))
    cmd = tool_command(payload.get("tool_input")) or extract_command(output)
    path = tool_path(payload.get("tool_input"))
    exit_code = extract_exit_code(output, text)
    bg = is_backgrounded(output, text, payload.get("tool_input"))
    crash = bool(CRASH_RE.search(text))

    if tool in ("Shell", "AwaitShell") and exit_code in (0, None) and not crash and not bg:
        resolve_soft_shell_failures(state, cmd, text)

    if bg:
        record_background(state, payload, cmd, text, output)
        return (
            "FAILURE WATCH: a command was backgrounded. Do not assume it succeeded. "
            "Check the terminal output / exit code before continuing.\n%s"
            % clip(cmd or tool, 200)
        )

    if tool in EDIT_TOOLS and looks_like_edit_error(text):
        record(
            state,
            kind="edit_failure",
            summary="%s reported an error: %s" % (tool, clip(text, 160)),
            detail=text,
            tool=tool,
            path=path,
            command=cmd,
            generation_id=payload.get("generation_id"),
        )
        return "FAILURE WATCH: edit did not apply cleanly on %s. Re-read and retry." % (
            path or "the target file"
        )

    if tool not in ("Shell", "AwaitShell") and not crash:
        return None

    if expected_nonzero(cmd, exit_code):
        return None

    if crash or is_crash_exit(exit_code):
        label = signal_name(exit_code) if is_crash_exit(exit_code) else "crash signature"
        record(
            state,
            kind="background_crash" if bg else "silent_shell_failure",
            summary="crash (%s): %s" % (label, clip(cmd or tool, 160)),
            detail=text,
            tool=tool,
            command=cmd,
            exit_code=exit_code,
            generation_id=payload.get("generation_id"),
        )
        return (
            "FAILURE WATCH: command crashed (%s). Do not treat this as success.\n%s"
            % (label, clip(cmd or tool, 200))
        )

    if exit_code not in (None, 0) and is_silent_failure(text, exit_code):
        record(
            state,
            kind="silent_shell_failure",
            summary="exit %s with little/no output: %s" % (exit_code, clip(cmd or tool, 140)),
            detail=text,
            tool=tool,
            command=cmd,
            exit_code=exit_code,
            generation_id=payload.get("generation_id"),
        )
        return (
            "FAILURE WATCH: command failed silently (exit %s, little/no output).\n%s"
            % (exit_code, clip(cmd or tool, 200))
        )
    return None


def handle_after_shell(state: dict[str, Any], payload: dict[str, Any]) -> str | None:
    cmd = str(payload.get("command") or "")
    text = str(payload.get("output") or "")
    exit_code = extract_exit_code(None, text)
    bg = bool(BG_RE.search(text))
    crash = bool(CRASH_RE.search(text))

    if bg:
        record_background(state, payload, cmd, text, None)
        return (
            "FAILURE WATCH: shell command is running in the background. "
            "Wait for exit_code before assuming success.\n%s" % clip(cmd, 200)
        )

    if expected_nonzero(cmd, exit_code):
        return None

    if crash or is_crash_exit(exit_code):
        label = signal_name(exit_code) if is_crash_exit(exit_code) else "crash signature"
        record(
            state,
            kind="silent_shell_failure",
            summary="crash (%s): %s" % (label, clip(cmd, 160)),
            detail=text,
            tool="Shell",
            command=cmd,
            exit_code=exit_code,
            generation_id=payload.get("generation_id"),
        )
        return "FAILURE WATCH: shell crashed (%s).\n%s" % (label, clip(cmd, 200))

    if exit_code not in (None, 0) and is_silent_failure(text, exit_code):
        record(
            state,
            kind="silent_shell_failure",
            summary="exit %s with little/no output: %s" % (exit_code, clip(cmd, 140)),
            detail=text,
            tool="Shell",
            command=cmd,
            exit_code=exit_code,
            generation_id=payload.get("generation_id"),
        )
        return (
            "FAILURE WATCH: shell failed silently (exit %s).\n%s"
            % (exit_code, clip(cmd, 200))
        )
    return None


def handle_after_file_edit(state: dict[str, Any], payload: dict[str, Any]) -> None:
    path = str(payload.get("file_path") or "")
    if not path:
        return
    kept = []
    for ev in state.get("events") or []:
        if ev.get("kind") == "edit_failure" and ev.get("path") == path and not ev.get("notified"):
            continue
        kept.append(ev)
    state["events"] = kept


def handle_subagent_stop(state: dict[str, Any], payload: dict[str, Any]) -> None:
    status = str(payload.get("status") or "")
    if status not in ("error", "aborted"):
        return
    kind = "subagent_crash" if status == "error" else "subagent_aborted"
    record(
        state,
        kind=kind,
        summary="subagent %s (%s): %s"
        % (status, payload.get("subagent_type") or "unknown", clip(payload.get("task") or "", 140)),
        detail=str(payload.get("summary") or ""),
        tool="Task",
        generation_id=payload.get("generation_id"),
    )


def handle_session_end(state: dict[str, Any], payload: dict[str, Any]) -> None:
    reason = str(payload.get("reason") or "")
    unexpected_bg = bool(payload.get("is_background_agent")) and reason not in (
        "completed",
        "user_close",
        "window_close",
        "",
    )
    if reason == "error" or unexpected_bg:
        record(
            state,
            kind="session_crash",
            summary="session ended (%s)%s"
            % (
                reason,
                " [background agent]" if payload.get("is_background_agent") else "",
            ),
            detail=str(payload.get("error_message") or payload.get("final_status") or ""),
            generation_id=payload.get("generation_id"),
        )


def handle_stop(state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    status = str(payload.get("status") or "completed")
    if status == "aborted":
        save_state(state)
        return {}

    scan_background_jobs(state, payload)
    pending = [
        ev
        for ev in state.get("events") or []
        if not ev.get("notified")
        and not ev.get("resolved")
        and ev.get("kind") != "subagent_aborted"
        and not is_missing_file_probe(str(ev.get("tool") or ""), str(ev.get("detail") or ev.get("summary") or ""))
        and not stale_or_benign(ev)
    ]
    if not pending:
        save_state(state)
        return {}

    lines = [
        "FAILURE WATCH: unresolved failures from this session. Do not assume they succeeded.",
        "Inspect each item, fix or report it, then continue.",
        "",
    ]
    for i, ev in enumerate(pending[:12], 1):
        extra = []
        if ev.get("path"):
            extra.append(ev["path"])
        if ev.get("exit_code") not in (None, ""):
            extra.append("exit %s" % ev["exit_code"])
        suffix = " (%s)" % ", ".join(extra) if extra else ""
        lines.append("%s. [%s] %s%s" % (i, ev.get("kind"), ev.get("summary"), suffix))
    if len(pending) > 12:
        lines.append("… %s more (see ~/.cursor/hooks/logs/failure-watch.log)" % (len(pending) - 12))

    for ev in pending:
        ev["notified"] = True
    save_state(state)
    msg = "\n".join(lines)
    log("stop follow-up (%s pending, status=%s)" % (len(pending), status))
    return {"followup_message": msg}


def stale_or_benign(ev: dict[str, Any]) -> bool:
    """Re-judge a stored event with current rules before reporting it.

    Events recorded by an older build can carry a prefixed command or a missing
    exit code, so re-derive both rather than trusting what was persisted.
    """
    tool = str(ev.get("tool") or "Shell")
    detail = str(ev.get("detail") or ev.get("summary") or "")
    cmd = strip_env_prefix(str(ev.get("command") or ""))
    code = ev.get("exit_code")
    if code is None:
        m = EXIT_TEXT_RE.search(detail)
        code = int(m.group(1)) if m else extract_exit_code(None, detail)
    return benign_shell_noise_reason(tool, detail, cmd) is not None or expected_nonzero(
        cmd, code
    )


def scan_background_jobs(state: dict[str, Any], payload: dict[str, Any]) -> None:
    jobs = list(state.get("background_jobs") or [])
    for job in jobs:
        path = job.get("output_file")
        if not path:
            continue
        info = read_terminal_file(Path(path))
        if not info:
            continue
        exit_code = info.get("exit_code")
        text = info.get("text") or ""
        if info.get("running"):
            record(
                state,
                kind="background_job",
                summary="still running: %s" % clip(job.get("command") or path, 160),
                detail="pid %s still running in %s" % (info.get("pid") or "?", path),
                tool="Shell",
                command=job.get("command"),
                path=path,
                generation_id=payload.get("generation_id"),
            )
            continue
        if exit_code in (None, 0) and not CRASH_RE.search(text):
            continue
        if expected_nonzero(job.get("command") or "", exit_code):
            continue
        kind = "background_crash" if (CRASH_RE.search(text) or is_crash_exit(exit_code)) else "silent_shell_failure"
        record(
            state,
            kind=kind,
            summary="background job ended exit %s: %s"
            % (exit_code if exit_code is not None else "?", clip(job.get("command") or path, 140)),
            detail=text,
            tool="Shell",
            command=job.get("command"),
            path=path,
            exit_code=exit_code,
            generation_id=payload.get("generation_id"),
        )

    for root in payload.get("workspace_roots") or []:
        scan_workspace_terminals(state, str(root), payload.get("generation_id"))


def scan_workspace_terminals(state: dict[str, Any], workspace_root: str, generation_id: Any) -> None:
    slug = workspace_root.lstrip("/").replace("/", "-")
    term_dir = Path.home() / ".cursor" / "projects" / slug / "terminals"
    if not term_dir.is_dir():
        return
    cutoff = time.time() - 2 * 3600
    known = {job.get("output_file") for job in state.get("background_jobs") or []}
    for path in sorted(term_dir.glob("*.txt"))[-20:]:
        if str(path) in known:
            continue
        try:
            if path.stat().st_mtime < cutoff:
                continue
        except OSError:
            continue
        info = read_terminal_file(path)
        if not info or info.get("running"):
            continue
        exit_code = info.get("exit_code")
        text = info.get("text") or ""
        cmd = info.get("command") or ""
        if not (CRASH_RE.search(text) or is_crash_exit(exit_code)):
            continue
        if expected_nonzero(cmd, exit_code):
            continue
        record(
            state,
            kind="background_crash",
            summary="terminal crash exit %s: %s"
            % (exit_code if exit_code is not None else "?", clip(cmd or str(path), 140)),
            detail=text,
            tool="Shell",
            command=cmd,
            path=str(path),
            exit_code=exit_code,
            generation_id=generation_id,
        )


def read_terminal_file(path: Path) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    pid_m = PID_RE.search(text)
    exits = [int(x) for x in EXIT_RE.findall(text)]
    running = bool(re.search(r"running_for_ms:", text)) and "exit_code:" not in text[-400:]
    cmd_m = re.search(r"last_command:\s*(.+)", text)
    return {
        "text": text[-4000:],
        "pid": int(pid_m.group(1)) if pid_m else None,
        "exit_code": exits[-1] if exits else None,
        "running": running,
        "command": cmd_m.group(1).strip() if cmd_m else "",
    }


def record_background(
    state: dict[str, Any],
    payload: dict[str, Any],
    cmd: str,
    text: str,
    output: Any,
) -> None:
    path = extract_terminal_file(text) or extract_terminal_file(stringify(output))
    pid_m = PID_RE.search(text)
    job = {
        "command": clip(cmd, 300),
        "output_file": path,
        "pid": int(pid_m.group(1)) if pid_m else None,
        "ts": now_iso(),
        "generation_id": payload.get("generation_id"),
    }
    jobs = state.setdefault("background_jobs", [])
    key = (job["output_file"], job["pid"], job["command"])
    for existing in jobs:
        if (existing.get("output_file"), existing.get("pid"), existing.get("command")) == key:
            return
    jobs.append(job)
    state["background_jobs"] = jobs[-20:]


def record(state: dict[str, Any], **fields: Any) -> None:
    summary = clip(str(fields.get("summary") or "failure"), MAX_SUMMARY)
    key_src = "|".join(
        [
            str(fields.get("kind") or ""),
            str(fields.get("tool") or ""),
            str(fields.get("path") or ""),
            str(fields.get("command") or "")[:180],
            str(fields.get("exit_code") if fields.get("exit_code") is not None else ""),
            summary[:120],
        ]
    )
    ev_id = hashlib.sha1(key_src.encode("utf-8")).hexdigest()[:16]
    events: list[dict[str, Any]] = state.setdefault("events", [])
    for ev in events:
        if ev.get("id") == ev_id:
            return
    event = {
        "id": ev_id,
        "kind": fields.get("kind") or "tool_failure",
        "summary": summary,
        "detail": clip(str(fields.get("detail") or ""), MAX_DETAIL),
        "tool": fields.get("tool"),
        "path": fields.get("path"),
        "command": clip(str(fields.get("command") or ""), 300) or None,
        "exit_code": fields.get("exit_code"),
        "generation_id": fields.get("generation_id"),
        "ts": now_iso(),
        "notified": False,
    }
    events.append(event)
    state["events"] = events[-MAX_EVENTS:]
    log("%s | %s" % (event["kind"], event["summary"]))


_resolved_state_dir: Path | None = None
_resolved_log_path: Path | None = None


def _dir_is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def resolved_state_dir() -> Path:
    global _resolved_state_dir
    if _resolved_state_dir is not None:
        return _resolved_state_dir
    for candidate in (STATE_DIR, FALLBACK_ROOT / "state"):
        if _dir_is_writable(candidate):
            _resolved_state_dir = candidate
            return candidate
    _resolved_state_dir = STATE_DIR
    return STATE_DIR


def resolved_log_path() -> Path:
    global _resolved_log_path
    if _resolved_log_path is not None:
        return _resolved_log_path
    if _dir_is_writable(LOG_PATH.parent):
        _resolved_log_path = LOG_PATH
        return LOG_PATH
    fallback = FALLBACK_ROOT / "logs" / "failure-watch.log"
    _dir_is_writable(fallback.parent)
    _resolved_log_path = fallback
    return fallback


def load_state(conv: str) -> dict[str, Any]:
    for path in (STATE_DIR / _state_name(conv), FALLBACK_ROOT / "state" / _state_name(conv)):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("events", [])
                data.setdefault("background_jobs", [])
                return data
        except (OSError, json.JSONDecodeError):
            continue
    return {"conversation_id": conv, "events": [], "background_jobs": []}


def save_state(state: dict[str, Any]) -> None:
    path = resolved_state_dir() / _state_name(str(state.get("conversation_id") or "_unknown"))
    tmp = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        log("hook error: %s" % exc)


def _state_name(conv: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", conv)[:80] or "_unknown"
    return "%s.json" % safe


def state_path(conv: str) -> Path:
    return resolved_state_dir() / _state_name(conv)


def prune_old_state() -> None:
    cutoff = time.time() - 7 * 24 * 3600
    for folder in (STATE_DIR, FALLBACK_ROOT / "state"):
        if not folder.is_dir():
            continue
        for path in folder.glob("*.json"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                continue


def parse_maybe_json(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text[:1] in "{[":
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return value
    return value


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except TypeError:
        return str(value)


def extract_exit_code(parsed: Any, text: str) -> int | None:
    if isinstance(parsed, dict):
        for key in ("exitCode", "exit_code", "last_exit_code", "code"):
            if key in parsed and parsed[key] is not None:
                try:
                    return int(parsed[key])
                except (TypeError, ValueError):
                    pass
    matches = EXIT_RE.findall(text or "")
    if matches:
        try:
            return int(matches[-1])
        except ValueError:
            return None
    return None


def extract_command(parsed: Any) -> str:
    if isinstance(parsed, dict):
        for key in ("command", "cmd"):
            if parsed.get(key):
                return str(parsed[key])
    return ""


def extract_terminal_file(text: str) -> str | None:
    if not text:
        return None
    m = TERMINAL_FILE_RE.search(text)
    return m.group(1) if m else None


def strip_env_prefix(cmd: str) -> str:
    """Drop the agent-shell-env.sh zsh prelude so the real command is visible."""
    if not cmd:
        return ""
    stripped = ENV_PREFIX_RE.sub("", cmd, count=1)
    return stripped.strip() or cmd.strip()


def tool_command(tool_input: Any) -> str:
    parsed = parse_maybe_json(tool_input)
    if isinstance(parsed, dict):
        return strip_env_prefix(str(parsed.get("command") or parsed.get("cmd") or ""))
    return ""


def tool_path(tool_input: Any) -> str | None:
    parsed = parse_maybe_json(tool_input)
    if isinstance(parsed, dict):
        for key in ("path", "file_path", "target_notebook"):
            if parsed.get(key):
                return str(parsed[key])
    return None


def is_backgrounded(parsed: Any, text: str, tool_input: Any) -> bool:
    inp = parse_maybe_json(tool_input)
    if isinstance(inp, dict) and inp.get("block_until_ms") == 0:
        return True
    if isinstance(parsed, dict) and (
        parsed.get("background") or parsed.get("running") or parsed.get("output_file")
    ):
        return True
    return bool(BG_RE.search(text or ""))


def expected_nonzero(command: str, exit_code: int | None) -> bool:
    if exit_code in (None, 0):
        return False
    cmd = (command or "").strip()
    if not cmd:
        return False
    if OR_TRUE_RE.search(cmd):
        return True
    return bool(EXPECTED_NONZERO_RE.search(cmd)) and exit_code in (1, 2)


def is_crash_exit(exit_code: int | None) -> bool:
    return isinstance(exit_code, int) and exit_code >= 128


def signal_name(exit_code: int | None) -> str:
    if not isinstance(exit_code, int):
        return "signal"
    return SIGNAL_NAMES.get(exit_code, "signal %s" % (exit_code - 128 if exit_code >= 128 else exit_code))


def is_silent_failure(text: str, exit_code: int) -> bool:
    stripped = re.sub(r"(?s)^---.*?---\s*", "", text or "").strip()
    stripped = re.sub(r"exit_code:\s*-?\d+\s*", "", stripped)
    stripped = re.sub(r"elapsed_ms:\s*\d+\s*", "", stripped)
    stripped = re.sub(r"pid:\s*\d+\s*", "", stripped)
    if len(stripped) < 40:
        return True
    if exit_code not in (0,) and not stripped:
        return True
    return False


def looks_like_edit_error(text: str) -> bool:
    lowered = (text or "").lower()
    return any(
        needle in lowered
        for needle in (
            "not found",
            "fuzzy match",
            "failed to",
            "could not",
            "error applying",
            "old_string",
            "no changes",
        )
    ) and "successfully" not in lowered


def clip(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(message: str) -> None:
    line = "%s %s\n" % (now_iso(), message)
    dest = resolved_log_path()
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass
    sys.stderr.write("[failure-watch] %s\n" % message)


def emit(obj: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    main()

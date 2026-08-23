{ config, pkgs, ... }:

{
  home.username = "patricklarocque";
  home.homeDirectory = "/Users/patricklarocque";
  home.stateVersion = "24.11";

  # Baseline CLI tools via Nix. Language runtimes stay on mise unless migrated.
  home.packages = with pkgs; [
    alejandra
    bat
    direnv
    fd
    fzf
    gh
    git
    jq
    ripgrep
    shellcheck
    terraform
  ];

  programs.home-manager.enable = true;
}

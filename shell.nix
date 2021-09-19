{ python ? "3.9" }:
let
  pkgs = import ./nix;
  prettier = pkgs.writeShellScriptBin "prettier" ''
    ${pkgs.nodePackages.prettier}/bin/prettier \
    --plugin-search-dir "${pkgs.nodePackages.prettier-plugin-toml}/lib" \
    "$@"
  '';
  mkPoetryEnv = python: pkgs.poetry2nix.mkPoetryEnv {
    inherit python;
    projectDir = ./.;
    overrides = pkgs.poetry2nix.overrides.withDefaults (
      import ./poetry-overrides.nix { inherit pkgs; }
    );
    editablePackageSources = {
      numbsql = ./numbsql;
    };
  };
  shellHook = ''
    ${(import ./pre-commit.nix).pre-commit-check.shellHook}
  '';
  commonBuildInputs = with pkgs; [
    git
    niv
    nix-linter
    nixpkgs-fmt
    poetry
    prettier
    sqlite
    cachix
    commitizen
  ];
  name = "python${builtins.replaceStrings [ "." ] [ "" ] python}";
in
pkgs.mkShell {
  name = "numbsql-${name}";
  inherit shellHook;
  PYTHONPATH = builtins.toPath ./.;
  buildInputs = commonBuildInputs ++ [
    (mkPoetryEnv pkgs.${name})
  ];
}

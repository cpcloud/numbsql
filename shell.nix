let
  pkgs = import ./nix;
  poetryEnv = pkgs.poetry2nix.mkPoetryEnv {
    projectDir = ./.;
    editablePackageSources = {
      slumba = ./slumba;
    };
  };
  rlwrap-sqlite = pkgs.writeShellScriptBin "sqlite" ''
    ${pkgs.rlwrap}/bin/rlwrap ${pkgs.sqlite}/bin/sqlite "$@"
  '';
in pkgs.mkShell {
  name = "slumba";
  buildInputs = with pkgs; [
    clang-tools
    gcc
    niv
    poetry
    poetryEnv
    rlwrap-sqlite
  ];
}

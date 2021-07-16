let
  pkgs = import ./.;
  poetryEnv = pkgs.poetry2nix.mkPoetryEnv {
    projectDir = ./.;
    editablePackageSources = {
      slumba = ./slumba;
    };
  };
in pkgs.mkShell {
  buildInputs = with pkgs; [
    niv
    poetry
    poetryEnv
    sqlite
    rlwrap
    gcc
    clang-tools
  ];
}

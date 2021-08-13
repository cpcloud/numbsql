let
  pkgs = import ./nix;
  poetryEnv = pkgs.poetry2nix.mkPoetryEnv {
    projectDir = ./.;
    overrides = pkgs.poetry2nix.overrides.withDefaults (self: super: {
      llvmlite = super.llvmlite.overridePythonAttrs (old: {
        preConfigure = ''
          export LLVM_CONFIG=${pkgs.llvm.dev}/bin/llvm-config
        '';
      });
    });
    editablePackageSources = {
      slumba = ./slumba;
    };
  };
  rlwrap-sqlite = pkgs.writeShellScriptBin "rsqlite" ''
    ${pkgs.rlwrap}/bin/rlwrap ${pkgs.sqlite}/bin/sqlite3 "$@"
  '';
in
pkgs.mkShell {
  name = "slumba";
  buildInputs = with pkgs; [
    clang-tools
    niv
    poetry
    poetryEnv
    rlwrap-sqlite
    sqlite
  ];
}

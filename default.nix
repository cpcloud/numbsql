{ python ? "python3.9" }:
let
  pkgs = import ./nix;
  drv =
    { poetry2nix
    , python
    , lib
    , sqlite
    }:

    poetry2nix.mkPoetryApplication {
      inherit python;

      pyproject = ./pyproject.toml;
      poetrylock = ./poetry.lock;
      src = lib.cleanSource ./.;

      buildInputs = [ sqlite ];

      overrides = pkgs.poetry2nix.overrides.withDefaults (
        import ./poetry-overrides.nix {
          inherit (pkgs) llvm;
        }
      );

      checkPhase = ''
        function min() {
          [ "$1" -le "$2" ] && echo "$1" || echo "$2"
        }

        runHook preCheck
        pytest --benchmark-disable --numprocesses=$(min $(nproc) 8)
        runHook postCheck
      '';

      pythonImportsCheck = [ "numbsql" ];
    };
in
pkgs.callPackage drv {
  python = pkgs.${builtins.replaceStrings [ "." ] [ "" ] python};
}

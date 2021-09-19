{ python ? "3.9" }:
let
  pkgs = import ./nix;
  drv =
    { poetry2nix
    , python
    , lib
    , sqlite
    , stdenv
    }:

    poetry2nix.mkPoetryApplication {
      inherit python;

      pyproject = ./pyproject.toml;
      poetrylock = ./poetry.lock;
      src = lib.cleanSource ./.;

      buildInputs = [ sqlite ];

      overrides = pkgs.poetry2nix.overrides.withDefaults (
        import ./poetry-overrides.nix { inherit pkgs; }
      );

      preCheck = lib.optionalString stdenv.isDarwin ''
        export DYLD_LIBRARY_PATH=${sqlite.out}/lib
      '';

      checkPhase = ''
        runHook preCheck
        pytest --benchmark-disable --numprocesses auto
        runHook postCheck
      '';

      pythonImportsCheck = [ "numbsql" ];
    };
in
pkgs.callPackage drv {
  python = pkgs."python${builtins.replaceStrings [ "." ] [ "" ] python}";
}

{ python ? "python3.7" }:
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

      overrides = pkgs.poetry2nix.overrides.withDefaults (_: super: {
        llvmlite = super.llvmlite.overridePythonAttrs (_: {
          preConfigure = ''
            export LLVM_CONFIG=${pkgs.llvm.dev}/bin/llvm-config
          '';
        });
      });

      checkPhase = ''
        function min() {
          [ "$1" -le "$2" ] && echo "$1" || echo "$2"
        }

        runHook preCheck
        pytest --benchmark-disable --numprocesses=$(min $(nproc) 8)
        runHook postCheck
      '';
      # pytestCheckHook fails due to colliding versions of pytest and its
      # transitive dependencies
      pytestFlags = [ "--benchmark-disable" ];

      pythonImportsCheck = [ "slumba" ];
    };
in
pkgs.callPackage drv {
  python = pkgs.${builtins.replaceStrings [ "." ] [ "" ] python};
}

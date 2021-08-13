{ python ? "python3.7" }:
let
  pkgs = import ./nix;
  drv =
    { poetry2nix
    , python
    }:

    poetry2nix.mkPoetryApplication {
      inherit python;

      projectDir = ./.;
      overrides = pkgs.poetry2nix.overrides.withDefaults (_: super: {
        llvmlite = super.llvmlite.overridePythonAttrs (_: {
          preConfigure = ''
            export LLVM_CONFIG=${pkgs.llvm.dev}/bin/llvm-config
          '';
        });
      });
      checkPhase = ''
        runHook preCheck
        pytest --benchmark-disable
        runHook postCheck
      '';
      buildInputs = [ pkgs.sqlite ];
      pythonImportsCheck = [ "slumba" ];
    };
in
pkgs.callPackage drv {
  python = pkgs.${builtins.replaceStrings [ "." ] [ "" ] python};
}

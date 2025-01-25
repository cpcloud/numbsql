{ pkgs, deps }:
final: prev: {
  numbsql = prev.numbsql.overrideAttrs (old: {
    passthru = old.passthru // {
      tests = old.passthru.tests or { } // {
        pytest =
          let
            pythonEnv = final.mkVirtualEnv "numbsql-test-env" (deps // {
              # Use default dependencies from overlay.nix + enabled tests group.
              numbsql = deps.numbsql or [ ] ++ [ "tests" ];
            });
          in
          pkgs.stdenv.mkDerivation {
            name = "numbsql-test";
            nativeCheckInputs = [ pythonEnv pkgs.sqlite ];
            src = ../.;
            doCheck = true;

            preCheck = ''
              set -euo pipefail

              HOME="$(mktemp -d)"
              export HOME
            '';

            checkPhase = ''
              runHook preCheck
              pytest
              runHook postCheck
            '';

            NUMBA_CAPTURED_ERRORS = "new_style";
            installPhase = "mkdir $out";
          };
      };
    };
  });
}

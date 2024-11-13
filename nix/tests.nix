{ pkgs, deps }:
let
  inherit (pkgs) stdenv lib;
in
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
          stdenv.mkDerivation {
            name = "numbsql-test";
            nativeCheckInputs = [ pythonEnv pkgs.sqlite ];
            src = ../.;
            doCheck = true;

            preCheck = ''
              set -euo pipefail

              HOME="$(mktemp -d)"
              export HOME
            '' + lib.optionalString stdenv.isDarwin ''
              export DYLD_LIBRARY_PATH=${lib.getLib pkgs.sqlite}
            '';

            checkPhase = ''
              runHook preCheck
              pytest -vv -x --randomly-dont-reorganize
              runHook postCheck
            '';

            NUMBA_CAPTURED_ERRORS = "new_style";
            installPhase = "mkdir $out";
          };
      };
    };
  });
}

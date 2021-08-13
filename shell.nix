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
    overrides = pkgs.poetry2nix.overrides.withDefaults (_: super: {
      llvmlite = super.llvmlite.overridePythonAttrs (_: {
        preConfigure = ''
          export LLVM_CONFIG=${pkgs.llvm.dev}/bin/llvm-config
        '';
      });
    });
    editablePackageSources = {
      slumba = ./slumba;
    };
  };
  versions = [ "python37" "python38" "python39" ];
  conda-shell-run = pkgs.writeShellScriptBin "conda-shell-run" ''
    set -eu
    set -o pipefail
    set -o errexit
    set -o nounset
    ${pkgs.conda}/bin/conda-shell -c "$*"
  '';
in
pkgs.lib.listToAttrs
  (map
    (name: {
      inherit name;
      value = pkgs.mkShell {
        name = "slumba-dev-${name}";
        shellHook = ''
          ${(import ./pre-commit.nix).pre-commit-check.shellHook}
        '';
        buildInputs = (
          with pkgs; [
            clang-tools
            git
            niv
            nix-linter
            nixpkgs-fmt
            poetry
            prettier
            sqlite
          ]
        ) ++ [
          (mkPoetryEnv pkgs.${name})
          conda-shell-run
        ];
      };
    })
    versions)

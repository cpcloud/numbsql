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
    overrides = pkgs.poetry2nix.overrides.withDefaults (
      import ./poetry-overrides.nix {
        inherit (pkgs) llvm;
      }
    );
    editablePackageSources = {
      slumba = ./slumba;
    };
  };
  versions = [ "python37" "python38" "python39" ];
in
pkgs.lib.listToAttrs
  (map
    (name: {
      inherit name;
      value = pkgs.mkShell {
        name = "slumba-dev-${name}";
        PYTHONPATH = ".";
        shellHook = ''
          ${(import ./pre-commit.nix).pre-commit-check.shellHook}
        '';
        buildInputs = (
          with pkgs; [
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
        ];
      };
    })
    versions)

{
  description = "Numba UD(A)Fs for SQLite";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";

    gitignore = {
      url = "github:hercules-ci/gitignore.nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };

    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable-small";

    pre-commit-hooks = {
      url = "github:cachix/pre-commit-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };
  };

  outputs =
    { self
    , flake-utils
    , gitignore
    , nixpkgs
    , pre-commit-hooks
    , poetry2nix
    }:
    {
      overlay = nixpkgs.lib.composeManyExtensions [
        poetry2nix.overlay
        gitignore.overlay
        (pkgs: super: {
          prettierTOML = pkgs.writeShellScriptBin "prettier" ''
            ${pkgs.nodePackages.prettier}/bin/prettier \
            --plugin-search-dir "${pkgs.nodePackages.prettier-plugin-toml}/lib" \
            "$@"
          '';
        } // (super.lib.listToAttrs (
          super.lib.concatMap
            (py:
              let
                noDotPy = super.lib.replaceStrings [ "." ] [ "" ] py;
                overrides = pkgs.poetry2nix.overrides.withDefaults (
                  import ./poetry-overrides.nix {
                    inherit pkgs;
                    inherit (pkgs) lib stdenv;
                  }
                );
              in
              [
                {
                  name = "numbsql${noDotPy}";
                  value = pkgs.poetry2nix.mkPoetryApplication {
                    python = pkgs."python${noDotPy}";

                    pyproject = ./pyproject.toml;
                    poetrylock = ./poetry.lock;
                    src = pkgs.gitignoreSource ./.;

                    buildInputs = [ pkgs.sqlite ];

                    inherit overrides;

                    preCheck = pkgs.lib.optionalString pkgs.stdenv.isDarwin ''
                      export DYLD_LIBRARY_PATH=${pkgs.sqlite.out}/lib
                    '';

                    checkPhase = ''
                      runHook preCheck
                      pytest --benchmark-disable --numprocesses auto
                      runHook postCheck
                    '';

                    pythonImportsCheck = [ "numbsql" ];
                  };
                }
                {
                  name = "numbsqlDevEnv${noDotPy}";
                  value = pkgs.poetry2nix.mkPoetryEnv {
                    python = pkgs."python${noDotPy}";
                    projectDir = ./.;
                    inherit overrides;
                    editablePackageSources = {
                      numbsql = ./numbsql;
                    };
                  };
                }
              ])
            [ "3.7" "3.8" "3.9" ]
        )))
      ];
    } // (
      flake-utils.lib.eachDefaultSystem (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
            overlays = [ self.overlay ];
          };
          inherit (pkgs) lib;
        in
        rec {
          packages.numbsql37 = pkgs.numbsql37;
          packages.numbsql38 = pkgs.numbsql38;
          packages.numbsql39 = pkgs.numbsql39;

          defaultPackage = packages.numbsql39;

          checks = {
            pre-commit-check = pre-commit-hooks.lib.${system}.run {
              src = ./.;
              hooks = {
                nix-linter = {
                  enable = true;
                  entry = lib.mkForce "${pkgs.nix-linter}/bin/nix-linter";
                };

                nixpkgs-fmt = {
                  enable = true;
                  entry = lib.mkForce "${pkgs.nixpkgs-fmt}/bin/nixpkgs-fmt --check";
                };

                shellcheck = {
                  enable = true;
                  entry = "${pkgs.shellcheck}/bin/shellcheck";
                  files = "\\.sh$";
                };

                shfmt = {
                  enable = true;
                  entry = "${pkgs.shfmt}/bin/shfmt -i 2 -sr -d -s -l";
                  files = "\\.sh$";
                };

                prettier = {
                  enable = true;
                  entry = lib.mkForce "${pkgs.prettierTOML}/bin/prettier --check";
                  types_or = [ "json" "toml" "yaml" ];
                };

                black = {
                  enable = true;
                  entry = lib.mkForce "black --check";
                  types = [ "python" ];
                };

                isort = {
                  enable = true;
                  language = "python";
                  entry = lib.mkForce "isort --check";
                  types_or = [ "cython" "pyi" "python" ];
                };

                flake8 = {
                  enable = true;
                  language = "python";
                  entry = "flake8";
                  types = [ "python" ];
                };

                pyupgrade = {
                  enable = true;
                  entry = "pyupgrade --py37-plus";
                  types = [ "python" ];
                };

                mypy = {
                  enable = true;
                  entry = "mypy";
                  types = [ "python" ];
                };
              };
            };
          };

          devShell = pkgs.mkShell
            {
              nativeBuildInputs = with pkgs; [
                commitizen
                numbsqlDevEnv39
                poetry
                prettierTOML
                # useful for testing sqlite things with a sane CLI, i.e., with
                # readline
                sqlite-interactive
                # sqlite is necssary to ensure the availability of libsqlite3
                sqlite
              ];
              shellHook = self.checks.${system}.pre-commit-check.shellHook;
            } // pkgs.lib.optionalAttrs pkgs.stdenv.isDarwin {
            DYLD_LIBRARY_PATH = "${pkgs.sqlite.out}/lib";
          };
        }
      )
    );
}

{
  description = "Numba UD(A)Fs for SQLite";

  inputs = {
    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };

    flake-utils.url = "github:numtide/flake-utils";

    gitignore = {
      url = "github:hercules-ci/gitignore.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable-small";

    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs = {
        nixpkgs.follows = "nixpkgs";
        flake-utils.follows = "flake-utils";
      };
    };

    pre-commit-hooks = {
      url = "github:cachix/pre-commit-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { self
    , flake-utils
    , gitignore
    , nixpkgs
    , poetry2nix
    , pre-commit-hooks
    , ...
    }:
    let
      getOverrides = pkgs: pkgs.poetry2nix.overrides.withDefaults (
        import ./poetry-overrides.nix
      );
    in
    {
      overlays.default = nixpkgs.lib.composeManyExtensions [
        poetry2nix.overlays.default
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
                python = pkgs."python${py}";
              in
              [
                {
                  name = "numbsql${py}";
                  value = pkgs.poetry2nix.mkPoetryApplication {
                    inherit python;

                    projectDir = ./.;
                    src = pkgs.gitignoreSource ./.;
                    preferWheels = true;

                    buildInputs = [ pkgs.sqlite ];

                    overrides = getOverrides pkgs;

                    NUMBA_CAPTURED_ERRORS = "new_style";

                    preCheck = ''
                      export HOME="$(mktemp -d)"
                    '' + pkgs.lib.optionalString pkgs.stdenv.isDarwin ''
                      export DYLD_LIBRARY_PATH=${pkgs.sqlite.out}/lib
                    '';

                    checkPhase = ''
                      runHook preCheck
                      pytest --numprocesses auto
                      runHook postCheck
                    '';

                    pythonImportsCheck = [ "numbsql" ];
                  };
                }
                {
                  name = "numbsqlDevEnv${py}";
                  value = pkgs.poetry2nix.mkPoetryEnv {
                    inherit python;
                    overrides = getOverrides pkgs;
                    projectDir = ./.;
                    preferWheels = true;
                    editablePackageSources = {
                      numbsql = ./numbsql;
                    };
                  };
                }
              ])
            [ "39" "310" "311" "312" ]
        )))
      ];
    } // (
      flake-utils.lib.eachDefaultSystem (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
            overlays = [ self.overlays.default ];
          };
          inherit (pkgs) lib;
        in
        rec {
          packages.numbsql39 = pkgs.numbsql39;
          packages.numbsql310 = pkgs.numbsql310;
          packages.numbsql311 = pkgs.numbsql311;
          packages.numbsql312 = pkgs.numbsql312;

          packages.numbsql = pkgs.numbsql311;

          defaultPackage = packages.numbsql;

          checks = {
            pre-commit-check = pre-commit-hooks.lib.${system}.run {
              src = ./.;
              hooks = {
                ruff.enable = true;
                deadnix.enable = true;
                nixpkgs-fmt.enable = true;
                shellcheck.enable = true;
                statix.enable = true;
                mypy.enable = true;

                ruff-format = {
                  enable = true;
                  types = [ "python" ];
                  entry = "${pkgs.ruff}/bin/ruff format";
                };

                shfmt = {
                  enable = true;
                  files = "\\.sh$";
                  entry = lib.mkForce "shfmt -i 2 -sr -s";
                };

                prettier = {
                  enable = true;
                  types_or = [ "json" "toml" "yaml" ];
                };
              };
              settings.prettier.binPath = "${pkgs.prettierTOML}/bin/prettier";
            };
          };

          devShell = pkgs.mkShell
            {
              name = "numbsql";
              nativeBuildInputs = with pkgs; [
                numbsqlDevEnv311
                poetry
                prettierTOML
                # useful for testing sqlite things with a sane CLI, i.e., with
                # readline
                sqlite-interactive
                # sqlite is necessary to ensure the availability of libsqlite3
                sqlite
              ];
              inherit (self.checks.${system}.pre-commit-check) shellHook;
              NUMBA_CAPTURED_ERRORS = "new_style";
            } // pkgs.lib.optionalAttrs pkgs.stdenv.isDarwin {
            DYLD_LIBRARY_PATH = "${pkgs.sqlite.out}/lib";
            NIXPKGS_ALLOW_UNFREE = "1";
            JUPYTER_PLATFORM_DIRS = "1";
          };
        }
      )
    );
}

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

    pyproject-nix = {
      url = "github:nix-community/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:adisbladis/uv2nix";
      inputs = {
        pyproject-nix.follows = "pyproject-nix";
        nixpkgs.follows = "nixpkgs";
      };
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs = {
        pyproject-nix.follows = "pyproject-nix";
        uv2nix.follows = "uv2nix";
        nixpkgs.follows = "nixpkgs";
      };
    };

    git-hooks = {
      url = "github:cachix/git-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { self
    , flake-utils
    , gitignore
    , nixpkgs
    , uv2nix
    , git-hooks
    , pyproject-nix
    , pyproject-build-systems
    , ...
    }:
    {
      overlays.default = nixpkgs.lib.composeManyExtensions [
        gitignore.overlay
        (import ./nix/overlay.nix { inherit uv2nix pyproject-nix pyproject-build-systems; })
      ];
    }
    // (flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ self.overlays.default ];
        };
        inherit (pkgs) lib;
      in
      rec {
        packages.numbsql310 = pkgs.numbsql310;
        packages.numbsql311 = pkgs.numbsql311;
        packages.numbsql312 = pkgs.numbsql312;
        packages.numbsql313 = pkgs.numbsql313;

        packages.numbsql = pkgs.numbsql313;

        defaultPackage = packages.numbsql;

        checks = {
          pre-commit = git-hooks.lib.${system}.run {
            src = ./.;
            hooks = {
              ruff.enable = true;
              deadnix.enable = true;
              nixpkgs-fmt.enable = true;
              shellcheck.enable = true;
              statix.enable = true;
              mypy.enable = true;
              taplo.enable = true;

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
                types_or = [
                  "json"
                  "yaml"
                ];
              };
            };
          };
        };

        devShell =
          let
            sqlite3LdLibraryPath = lib.makeLibraryPath [ pkgs.sqlite ];
            env = pkgs.numbsqlDevEnv313;
          in
          pkgs.mkShell
            {
              inherit (env) name;
              nativeBuildInputs = with pkgs; [
                env
                uv
                # useful for testing sqlite things with a sane CLI, i.e., with
                # readline
                sqlite-interactive
              ];
              inherit (self.checks.${system}.pre-commit) shellHook;
              NUMBA_CAPTURED_ERRORS = "new_style";
              LD_LIBRARY_PATH = sqlite3LdLibraryPath;
            }
          // pkgs.lib.optionalAttrs pkgs.stdenv.isDarwin {
            DYLD_LIBRARY_PATH = sqlite3LdLibraryPath;
            NIXPKGS_ALLOW_UNFREE = "1";
            JUPYTER_PLATFORM_DIRS = "1";
          };
      }
    ));
}

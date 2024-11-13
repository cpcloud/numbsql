{ uv2nix, pyproject-nix }: final: prev:
let
  pkgs = final;
  inherit (pkgs) lib;

  # Create package overlay from workspace.
  workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ../.; };

  envOverlay = workspace.mkPyprojectOverlay {
    sourcePreference = "wheel";
  };

  # Create an overlay enabling editable mode for all local dependencies.
  # This is for usage with `nix develop`
  editableOverlay =
    workspace.mkEditablePyprojectOverlay {
      root = "$REPO_ROOT";
    };

  # Build fixups overlay
  pyprojectOverrides = import ./pyproject-overrides.nix { inherit pkgs; };

  # Adds tests to passthru.tests
  testOverlay = import ./tests.nix {
    inherit pkgs;
    deps = defaultDeps;
  };

  # Default dependencies for env
  defaultDeps.numbsql = [ ];

  mkEnv' =
    {
      # Python dependency specification
      deps
    , # Installs the package as an editable package for use with `nix develop`.
      # This means that any changes done to your local files do not require a rebuild.
      editable
    ,
    }: python:
    let
      # Construct package set
      pythonSet =
        # Use base package set from pyproject.nix builders
        (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        }).overrideScope
          (lib.composeManyExtensions ([
            envOverlay
            pyprojectOverrides
          ]
          ++ lib.optionals editable [ editableOverlay ]
          ++ lib.optionals (!editable) [ testOverlay ]));
    in
    # Build virtual environment
    (pythonSet.mkVirtualEnv "numbsql-${python.pythonVersion}" deps).overrideAttrs (_old: {
      # Add passthru.tests from numbsql to venv passthru.
      # This is used to build tests by CI.
      passthru = {
        inherit (pythonSet.numbsql.passthru) tests;
      };
    });

  mkEnv = mkEnv' {
    deps = defaultDeps;
    editable = false;
  };

  mkDevEnv = mkEnv' {
    # Enable all dependencies for development shell
    deps = workspace.deps.all;
    editable = true;
  };
in
{
  prettierTOML = final.writeShellScriptBin "prettier" ''
    ${final.nodePackages.prettier}/bin/prettier \
    --plugin-search-dir "${final.nodePackages.prettier-plugin-toml}/lib" \
    "$@"
  '';
} // (prev.lib.listToAttrs (
  prev.lib.concatMap
    (py:
      [
        {
          name = "numbsql${py}";
          value = mkEnv final."python${py}";
        }
        {
          name = "numbsqlDevEnv${py}";
          value = mkDevEnv final."python${py}";
        }
      ])
    [ "310" "311" "312" ]
))

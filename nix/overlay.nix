{ uv2nix
, pyproject-nix
, pyproject-build-systems
}: pkgs: _:
let
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
      inherit (pkgs) lib stdenv;
      inherit (stdenv) targetPlatform;
      # Construct package set
      pythonSet =
        # Use base package set from pyproject.nix builders
        (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
          stdenv = stdenv.override {
            targetPlatform = targetPlatform // {
              darwinSdkVersion = if targetPlatform.isAarch64 then "14.0" else "12.0";
            };
          };
        }).overrideScope
          (lib.composeManyExtensions ([
            pyproject-build-systems.overlays.default
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
  numbsql310 = mkEnv pkgs.python310;
  numbsql311 = mkEnv pkgs.python311;
  numbsql312 = mkEnv pkgs.python312;

  numbsqlDevEnv310 = mkDevEnv pkgs.python310;
  numbsqlDevEnv311 = mkDevEnv pkgs.python311;
  numbsqlDevEnv312 = mkDevEnv pkgs.python312;

  ibisSmallDevEnv = mkEnv'
    {
      deps = {
        ibis-framework = [ "dev" ];
      };
      editable = false;
    }
    pkgs.python312;

  uv = uv2nix.packages.${pkgs.system}.uv-bin;
}

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
      import ./poetry-overrides.nix { }
    );
    editablePackageSources = {
      numbsql = ./numbsql;
    };
  };
  shellHook = ''
    ${(import ./pre-commit.nix).pre-commit-check.shellHook}
  '';
  commonBuildInputs = with pkgs; [
    git
    niv
    nix-linter
    nixpkgs-fmt
    poetry
    prettier
    sqlite
    cachix
    commitizen
  ];
  pythonVersions = [ "3.7" "3.8" "3.9" ];
in
{
  dev = pkgs.mkShell {
    name = "numbsql-build";
    inherit shellHook;
    buildInputs = commonBuildInputs;
  };
} // pkgs.lib.listToAttrs (
  map
    (name: {
      inherit name;
      value = pkgs.mkShell {
        name = "numbsql-${name}";
        inherit shellHook;
        PYTHONPATH = builtins.toPath ./.;
        buildInputs = commonBuildInputs ++ [
          (mkPoetryEnv pkgs.${name})
        ];
      };
    })
    (map
      (version: "python${builtins.replaceStrings [ "." ] [ "" ] version}")
      pythonVersions)
)

{ pkgs }: final: prev:
let
  inherit (pkgs) lib;
  inherit (final) resolveBuildSystem;

  addBuildSystems =
    pkg: spec:
    pkg.overrideAttrs (old: {
      nativeBuildInputs = old.nativeBuildInputs ++ resolveBuildSystem spec;
    });

  buildSystemOverrides = {
    # $package.$buildDep = [ ];
    #
    # e.g.:
    #
    # packaging.flit-core = [ ];
  };
in
lib.mapAttrs (name: spec: addBuildSystems prev.${name} spec) buildSystemOverrides // {
  numba = prev.numba.overrideAttrs (attrs: {
    nativeBuildInputs = attrs.nativeBuildInputs or [ ] ++ [ pkgs.tbb_2021_11 ];
  });
}

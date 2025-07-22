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
    llvmlite.setuptools = [ ];
    numpy.meson-python = [ ];
  };
in
lib.mapAttrs (name: spec: addBuildSystems prev.${name} spec) buildSystemOverrides // {
  hatchling = prev.hatchling.overrideAttrs (attrs: {
    propagatedBuildInputs = attrs.propagatedBuildInputs or [ ] ++ [ final.editables ];
  });

  numba = prev.numba.overrideAttrs (attrs: {
    nativeBuildInputs = attrs.nativeBuildInputs or [ ] ++ [ final.setuptools ];
    buildInputs = attrs.buildInputs or [ ] ++ [ pkgs.tbb_2022 ];
  });
}

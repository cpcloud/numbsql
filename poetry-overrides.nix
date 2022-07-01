{ lib, pkgs, stdenv, ... }: self: super: {
  numba = super.numba.overridePythonAttrs (_: {
    NIX_CFLAGS_COMPILE = lib.optionalString
      stdenv.isDarwin
      "-I${lib.getDev pkgs.libcxx}/include/c++/v1";
  });

  traitlets = super.traitlets.overridePythonAttrs (attrs: {
    nativeBuildInputs = attrs.nativeBuildInputs or [ ] ++ [ self.flit-core ];
  });

  jupyter-client = super.jupyter-client.overridePythonAttrs (attrs: {
    nativeBuildInputs = attrs.nativeBuildInputs or [ ] ++ [ self.hatchling ];
  });

  ipykernel = super.ipykernel.overridePythonAttrs (attrs: {
    nativeBuildInputs = attrs.nativeBuildInputs or [ ] ++ [ self.hatchling ];
  });
}

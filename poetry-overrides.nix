self: super:
let
  inherit (self) pkgs;
  inherit (pkgs) lib stdenv;
in
{
  numba = super.numba.overridePythonAttrs (_: {
    NIX_CFLAGS_COMPILE = lib.optionalString
      stdenv.isDarwin
      "-I${lib.getDev pkgs.libcxx}/include/c++/v1";
  });
}

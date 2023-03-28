self: super:
let
  inherit (self) pkgs;
  inherit (pkgs) lib stdenv;
in
{
  llvmlite = super.llvmlite.override { preferWheel = false; };
  numba = (super.numba.override { preferWheel = false; }).overridePythonAttrs (_: {
    NIX_CFLAGS_COMPILE = lib.optionalString
      stdenv.isDarwin
      "-I${lib.getDev pkgs.libcxx}/include/c++/v1";
  });
}

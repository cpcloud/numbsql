self: super:
let
  inherit (self) pkgs;
  inherit (pkgs) lib stdenv;
  disabledMacOSWheels = [
    "debugpy"
  ];
in
{
  llvmlite = super.llvmlite.override { preferWheel = false; };
  numba = (super.numba.override { preferWheel = false; }).overridePythonAttrs (_: {
    NIX_CFLAGS_COMPILE = lib.optionalString
      stdenv.isDarwin
      "-I${lib.getDev pkgs.libcxx}/include/c++/v1";
  });
  # `wheel` cannot be used as a wheel to unpack itself, since that would
  # require itself (infinite recursion)
  wheel = super.wheel.override { preferWheel = false; };
} // super.lib.listToAttrs (
  map
    (name: {
      inherit name;
      value = super.${name}.override { preferWheel = !self.pkgs.stdenv.isDarwin; };
    })
    disabledMacOSWheels
)

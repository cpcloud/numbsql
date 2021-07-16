let
  sources = import ./sources.nix;
in
import sources.nixpkgs {
  overlays = [
    (self: super: {
      llvm = super.llvm_10;
    })
  ];
}

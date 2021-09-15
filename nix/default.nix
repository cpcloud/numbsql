let
  sources = import ./sources.nix;
in
import sources.nixpkgs {
  overlays = [
    (self: _: {
      llvm = self.llvm_11;
    })
  ];
}

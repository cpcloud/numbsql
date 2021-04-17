import (import ./nix/sources.nix).nixpkgs {
  overlays = [
    (self: super: {
      llvm = super.llvm_10;
    })
  ];
}

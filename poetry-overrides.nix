{ llvm }: self: super: {
  llvmlite = super.llvmlite.overridePythonAttrs (_: {
    preConfigure = ''
      export LLVM_CONFIG=${llvm.dev}/bin/llvm-config
    '';
  });

  tomli = super.tomli.overridePythonAttrs (old: {
    propagatedNativeBuildInputs = (old.propagatedNativeBuildInputs or [ ]) ++ [
      self.flit
    ];
  });

  pytest-randomly = super.pytest-randomly.overridePythonAttrs (old: {
    propagatedBuildInputs = (old.propagatedBuildInputs or [ ]) ++ [
      self.importlib-metadata
    ];
  });
}

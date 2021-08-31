{ llvm }: self: super: {
  llvmlite = super.llvmlite.overridePythonAttrs (_: {
    preConfigure = ''
      export LLVM_CONFIG=${llvm.dev}/bin/llvm-config
    '';
  });

  tomli = super.tomli.overridePythonAttrs (attrs: {
    propagatedNativeBuildInputs = (attrs.propagatedNativeBuildInputs or [ ]) ++ [
      self.flit
    ];
  });

  pytest-randomly = super.pytest-randomly.overridePythonAttrs (attrs: {
    propagatedBuildInputs = (attrs.propagatedBuildInputs or [ ]) ++ [
      self.importlib-metadata
    ];
  });

  jupyterlab-widgets = super.jupyterlab-widgets.overridePythonAttrs (attrs: {
    propagatedBuildInputs = (attrs.propagatedBuildInputs or [ ]) ++ [
      self.jupyter-packaging
    ];
  });

  watchdog = super.watchdog.overrideAttrs (attrs: {
    disabledTests = (attrs.disabledTests or [ ]) ++ [
      "test_move_to"
      "test_move_internal"
      "test_close_should_terminate_thread"
    ];
  });
}

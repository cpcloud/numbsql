{ ... }: self: super: {
  pytest-randomly = super.pytest-randomly.overrideAttrs (attrs: {
    propagatedBuildInputs = (attrs.propagatedBuildInputs or [ ]) ++ [
      self.importlib-metadata
    ];
    postPatch = "";
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

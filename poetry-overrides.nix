{ pkgs, ... }: self: super: {
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

  black = super.black.overridePythonAttrs (_: {
    dontPreferSetupPy = true;
  });

  numba = super.numba.overridePythonAttrs (_: {
    NIX_CFLAGS_COMPILE = pkgs.lib.optionalString
      pkgs.stdenv.isDarwin
      "-I${pkgs.lib.getDev pkgs.libcxx}/include/c++/v1";
  });
}

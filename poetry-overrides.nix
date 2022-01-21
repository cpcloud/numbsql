{ lib, pkgs, stdenv, ... }: self: super: {
  watchdog = super.watchdog.overrideAttrs (attrs: {
    disabledTests = (attrs.disabledTests or [ ]) ++ [
      "test_move_to"
      "test_move_internal"
      "test_close_should_terminate_thread"
    ];
  });

  numba = super.numba.overridePythonAttrs (_: {
    NIX_CFLAGS_COMPILE = lib.optionalString
      stdenv.isDarwin
      "-I${lib.getDev pkgs.libcxx}/include/c++/v1";
  });

  jupyter-core = super.jupyter-core.overridePythonAttrs (attrs: {
    buildInputs = (attrs.buildInputs or [ ]) ++ [ self.flit-core ];
  });

  typing-extensions = super.typing-extensions.overridePythonAttrs (attrs: {
    buildInputs = (attrs.buildInputs or [ ]) ++ [ self.flit-core ];
  });

  entrypoints = super.entrypoints.overridePythonAttrs (attrs: {
    nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ self.flit ];
  });

  isort = super.isort.overridePythonAttrs (attrs: {
    nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ self.poetry ];
  });
}

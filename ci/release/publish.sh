#!/usr/bin/env nix-shell
#!nix-shell --pure --keep POETRY_PYPI_TOKEN_PYPI -p cacert poetry -i bash
# shellcheck shell=bash

set -euo pipefail

poetry publish

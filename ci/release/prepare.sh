#!/usr/bin/env nix-shell
#!nix-shell -p cacert gnugrep unzip uv nix -i bash
# shellcheck shell=bash

set -euo pipefail

version="${1}"

# set version
uvx --from=toml-cli toml set --toml-path=pyproject.toml project.version "$version"

# build artifacts
uv build

# ensure that the built wheel has the correct version number
unzip -p "dist/numbsql-${version}-py3-none-any.whl" numbsql/__init__.py | grep -q "__version__ = \"$version\""

#!/usr/bin/env nix-shell
#!nix-shell -p cacert gnugrep unzip uv python3 -i bash
# shellcheck shell=bash

set -euo pipefail

version="${1}"

# set version
uvx --from=toml-cli toml set --toml-path=pyproject.toml project.version "$version"

# generate lock file with new version
uv sync --python "$(which python)" --all-extras --group dev --group tests --no-install-project --no-install-workspace

# build artifacts
uv build --python "$(which python)"

# ensure that the built wheel has the correct version number
unzip -p "dist/numbsql-${version}-py3-none-any.whl" numbsql/__init__.py | grep -q "__version__ = \"$version\""

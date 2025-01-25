#!/usr/bin/env nix-shell
#!nix-shell -I nixpkgs=channel:nixos-unstable-small --pure --keep UV_PUBLISH_TOKEN -p uv which python3 -i bash
# shellcheck shell=bash

set -euo pipefail

dry_run="${1:-false}"

# verify pyproject.toml and lock file
uv lock --python "$(which python)" --locked

# verify that we have a token available to push to pypi using set -u
if [ "${dry_run}" = "false" ]; then
  : "${UV_PUBLISH_TOKEN}"
fi

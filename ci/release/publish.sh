#!/usr/bin/env nix-shell
#!nix-shell --pure --keep UV_PUBLISH_TOKEN -p cacert uv -i bash
# shellcheck shell=bash

set -euo pipefail

uv publish

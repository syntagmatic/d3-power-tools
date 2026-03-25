#!/bin/bash
set -e
container exec -it -e GIT_CONFIG_GLOBAL=/workspace/.gitconfig "${1:-claude}" /bin/zsh

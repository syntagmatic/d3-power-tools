#!/bin/bash
set -e
container exec -it "${1:-claude}" /bin/zsh

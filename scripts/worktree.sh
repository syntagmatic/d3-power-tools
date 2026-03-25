#!/bin/bash
# Create a git worktree and optionally launch Claude Code in it.
#
# Usage:
#   ./scripts/worktree.sh <name>          # create worktree + open Claude
#   ./scripts/worktree.sh <name> --no-claude  # create worktree only
#   ./scripts/worktree.sh --list          # list active worktrees
#   ./scripts/worktree.sh --remove <name> # remove a worktree

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
PARENT="$(dirname "$REPO_ROOT")"
PREFIX="d3-pt"

usage() {
  echo "Usage: $0 <name> [--no-claude]"
  echo "       $0 --list"
  echo "       $0 --remove <name>"
  exit 1
}

[ $# -eq 0 ] && usage

case "$1" in
  --list|-l)
    git worktree list
    ;;
  --remove|-r)
    [ -z "$2" ] && usage
    git worktree remove "$PARENT/$PREFIX-$2"
    git branch -d "session/$2" 2>/dev/null && echo "Deleted branch session/$2" || true
    ;;
  --help|-h)
    usage
    ;;
  *)
    NAME="$1"
    WORKTREE="$PARENT/$PREFIX-$NAME"
    BRANCH="session/$NAME"

    if [ -d "$WORKTREE" ]; then
      echo "Worktree already exists at $WORKTREE"
      echo "cd $WORKTREE"
    else
      git worktree add "$WORKTREE" -b "$BRANCH"
      echo "Created worktree at $WORKTREE (branch: $BRANCH)"
    fi

    if [ "$2" != "--no-claude" ]; then
      cd "$WORKTREE"
      exec claude
    fi
    ;;
esac

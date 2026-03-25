#!/bin/bash
# Create a git worktree and optionally launch Claude Code in it.
#
# Usage:
#   ./scripts/worktree.sh <name>              # create worktree + open Claude
#   ./scripts/worktree.sh <name> --no-claude  # create worktree only
#   ./scripts/worktree.sh --rebase [<name>]    # rebase session onto main + fast-forward
#   ./scripts/worktree.sh --list              # list active worktrees
#   ./scripts/worktree.sh --remove <name>     # remove a worktree

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
PARENT="$(dirname "$REPO_ROOT")"
PREFIX="d3-pt"

usage() {
  echo "Usage: $0 <name> [--no-claude]"
  echo "       $0 --rebase [<name>]"
  echo "       $0 --list"
  echo "       $0 --remove <name>"
  exit 1
}

[ $# -eq 0 ] && usage

case "$1" in
  --list|-l)
    git worktree list
    ;;
  --rebase|-r)
    # Rebase session branch onto main, then fast-forward main (no merge commits).
    # If <name> is omitted, infers from current branch (session/<name>).
    if [ -n "$2" ]; then
      BRANCH="session/$2"
    else
      BRANCH="$(git symbolic-ref --short HEAD)"
      if [[ "$BRANCH" != session/* ]]; then
        echo "Error: not on a session branch and no name given" >&2
        exit 1
      fi
    fi

    # Fetch latest main from remote before rebasing
    git fetch origin main 2>/dev/null || true

    # Rebase onto main (no-op if already up to date)
    git rebase origin/main "$BRANCH"

    # Fast-forward main to the rebased tip.
    MAIN_WORKTREE="$(git worktree list --porcelain | awk '/^worktree /{wt=$2} /^branch refs\/heads\/main$/{print wt}')"
    NEW_TIP="$(git rev-parse "$BRANCH")"
    if [ -n "$MAIN_WORKTREE" ]; then
      # merge --ff-only updates ref + index + working tree atomically.
      # Refuses safely if dirty files conflict with incoming changes.
      git -C "$MAIN_WORKTREE" merge --ff-only "$BRANCH"
    else
      git update-ref refs/heads/main "$NEW_TIP"
    fi
    echo "Rebased $BRANCH onto main (fast-forward to $(git rev-parse --short "$NEW_TIP"))"
    ;;
  --remove|-R)
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

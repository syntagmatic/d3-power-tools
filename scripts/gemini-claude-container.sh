#!/bin/bash
set -e

IMAGE="gemini-cli-sandbox-playwright"
NAME="${1:-gemini}"
SCRIPT="$0"
while [ -h "$SCRIPT" ]; do
  DIR="$( cd -P "$( dirname "$SCRIPT" )" && pwd )"
  SCRIPT="$(readlink "$SCRIPT")"
  [[ $SCRIPT != /* ]] && SCRIPT="$DIR/$SCRIPT"
done
SCRIPT_DIR="$( cd -P "$( dirname "$SCRIPT" )" && pwd )"
PROJECT="${2:-.}"
PROJECT="$(cd "$PROJECT" && pwd)"

# Build image if missing
if ! container image list 2>/dev/null | grep -q "$IMAGE"; then
        echo "Building $IMAGE..."
        container build -t "$IMAGE" -f "$SCRIPT_DIR/../.gemini/devcontainer/Dockerfile" "$SCRIPT_DIR/../.gemini/devcontainer/"
fi

# Run the container, dropping directly into a tmux session
container run -it --rm \
        --name "$NAME" \
        --cpus 4 --memory 8G \
        -v "$PROJECT:/workspace" \
        -v "$HOME/.gemini:/home/node/.gemini" \
        -v "$HOME/.claude:/home/node/.claude" \
        -v "$HOME/.ssh:/home/node/.ssh:ro" \
        -e GIT_CONFIG_GLOBAL=/workspace/.gitconfig \
        -e COORD_SESSION_NAME="$NAME" \
        -e COORD_SESSION_ENV=container \
        -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
        -e GEMINI_API_KEY="${GEMINI_API_KEY:-}" \
        -e COLORTERM=truecolor \
        -e TERM=xterm-256color \
        -e LANG=C.UTF-8 \
        -e LC_ALL=C.UTF-8 \
        -u node -w /workspace \
        "$IMAGE" \
        tmux new-session -s "$NAME" -n "Claude" "claude --dangerously-skip-permissions" \; \
        new-window -n "Gemini" "gemini" \; \
        new-window -n "Shell" "zsh" \; \
        select-window -t 1

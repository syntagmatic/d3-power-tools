 #!/bin/bash
set -e

IMAGE="claude-code-sandbox-playwright"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT="${1:-.}"
PROJECT="$(cd "$PROJECT" && pwd)"

# Build image if missing
if ! container image list 2>/dev/null | grep -q "$IMAGE"; then
	echo "Building $IMAGE..."
	container build -t "$IMAGE" -f "$SCRIPT_DIR/../.claude/devcontainer/Dockerfile" "$SCRIPT_DIR/../.claude/devcontainer/"
fi

# No ANTHROPIC_API_KEY — use Max subscription OAuth
container run -it --rm \
	--cpus 4 --memory 8G \
	-v "$PROJECT:/workspace" \
	-v "$HOME/.claude:/home/node/.claude" \
	-v "$HOME/.ssh:/home/node/.ssh:ro" \
	-v "$HOME/.gitconfig:/tmp/.gitconfig:ro" \
	-e GIT_CONFIG_GLOBAL=/tmp/.gitconfig \
	-u node -w /workspace \
	"$IMAGE" \
	claude --dangerously-skip-permissions "${@:2}"

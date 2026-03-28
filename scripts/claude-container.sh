 #!/bin/bash
set -e

IMAGE="claude-code-sandbox-playwright"
NAME="${1:-claude}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT="${2:-.}"
PROJECT="$(cd "$PROJECT" && pwd)"

# Build image if missing
if ! container image list 2>/dev/null | grep -q "$IMAGE"; then
	echo "Building $IMAGE..."
	container build -t "$IMAGE" -f "$SCRIPT_DIR/../.claude/devcontainer/Dockerfile" "$SCRIPT_DIR/../.claude/devcontainer/"
fi

# No ANTHROPIC_API_KEY — use Max subscription OAuth
container run -it --rm \
	--name "$NAME" \
	--cpus 4 --memory 8G \
	-v "$PROJECT:/workspace" \
	-v "$HOME/.claude:/home/node/.claude" \
	-v "$HOME/.ssh:/home/node/.ssh:ro" \
	-e GIT_CONFIG_GLOBAL=/workspace/.gitconfig \
	-e COORD_SESSION_NAME="$NAME" \
	-e COORD_SESSION_ENV=container \
	-u node -w /workspace \
	"$IMAGE" \
	claude --dangerously-skip-permissions "${@:3}"

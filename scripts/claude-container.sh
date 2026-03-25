 #!/bin/bash
set -e

PROJECT="${1:-.}"
PROJECT="$(cd "$PROJECT" && pwd)"

# No ANTHROPIC_API_KEY — use Max subscription OAuth
container run -it --rm \
	--cpus 4 --memory 8G \
	-v "$PROJECT:/workspace" \
	-v "$HOME/.claude:/home/node/.claude" \
	-v "$HOME/.ssh:/home/node/.ssh:ro" \
	-v "$HOME/.gitconfig:/tmp/.gitconfig:ro" \
	-e GIT_CONFIG_GLOBAL=/tmp/.gitconfig \
	-u node -w /workspace \
	claude-code-sandbox \
	claude --dangerously-skip-permissions "${@:2}"

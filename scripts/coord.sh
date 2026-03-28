#!/bin/bash
# Multi-Claude session coordination.
#
# All state lives in .git/coordination/ (shared across worktrees, visible
# to containers via the project mount, auto-gitignored).
#
# Usage:
#   coord.sh register <name> <env>        Register this session
#   coord.sh heartbeat                    Update heartbeat
#   coord.sh status <description>         Set current task
#   coord.sh files <file>...              Declare active files
#   coord.sh done                         Mark session complete
#   coord.sh deregister                   Remove session
#
#   coord.sh list                         List all sessions
#   coord.sh conflicts                    Show file conflicts
#
#   coord.sh task-add <title> [desc]      Add a task
#   coord.sh task-claim <id>              Claim a task
#   coord.sh task-done <id>               Complete a task
#   coord.sh task-note <id> <text>        Add note to a task
#   coord.sh task-list                    Show all tasks
#
#   coord.sh gc                           Clean stale sessions

set -e

# --- paths ---

GIT_COMMON="$(git rev-parse --git-common-dir 2>/dev/null)" || {
  echo "Error: not in a git repository" >&2; exit 1
}
COORD="$GIT_COMMON/coordination"
SESSIONS="$COORD/sessions"
TASKS_FILE="$COORD/tasks.json"
LOCK_FILE="$COORD/tasks.lock"

mkdir -p "$SESSIONS"

# --- helpers ---

now_iso() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# Session identity: stored in .self file in the coordination dir, keyed by
# working directory hash so multiple worktrees don't collide.
wdir_hash() { echo -n "$(pwd)" | md5sum | cut -c1-8; }

self_file() {
  local f="$SESSIONS/.self.$(wdir_hash)"
  if [ -f "$f" ]; then
    cat "$f"
  else
    echo "Error: no session registered (run 'coord.sh register' first)" >&2
    exit 1
  fi
}

session_file() { echo "$SESSIONS/$1.json"; }

# Portable seconds-since-epoch from ISO timestamp
iso_to_epoch() {
  if date -d "2000-01-01T00:00:00Z" +%s &>/dev/null; then
    date -d "$1" +%s
  else
    date -jf "%Y-%m-%dT%H:%M:%SZ" "$1" +%s 2>/dev/null || echo 0
  fi
}

age_minutes() {
  local ts now
  ts=$(iso_to_epoch "$1")
  now=$(date -u +%s)
  echo $(( (now - ts) / 60 ))
}

with_task_lock() {
  (
    flock -x -w 5 200 2>/dev/null || true
    "$@"
  ) 200>"$LOCK_FILE"
}

ensure_tasks_file() {
  [ -f "$TASKS_FILE" ] || echo '{"tasks":[],"log":[]}' > "$TASKS_FILE"
}

next_task_id() {
  ensure_tasks_file
  local max
  max=$(jq -r '[.tasks[].id // "t0" | ltrimstr("t") | tonumber] | max // 0' "$TASKS_FILE")
  echo "t$(( max + 1 ))"
}

log_action() {
  local session="$1" action="$2"
  ensure_tasks_file
  local tmp="$TASKS_FILE.tmp.$$"
  jq --arg at "$(now_iso)" --arg s "$session" --arg a "$action" \
    '.log += [{"at":$at,"session":$s,"action":$a}]' "$TASKS_FILE" > "$tmp"
  mv "$tmp" "$TASKS_FILE"
}

# --- session commands ---

cmd_register() {
  local name="${1:?Usage: coord.sh register <name> <env>}"
  local env="${2:-host}"
  local branch wdir
  branch="$(git symbolic-ref --short HEAD 2>/dev/null || echo "detached")"
  wdir="$(pwd)"

  # Find the Claude process PID (best effort)
  local pid=0
  pid=$(pgrep -f "claude" 2>/dev/null | head -1) || pid=$$

  jq -n \
    --arg name "$name" \
    --arg env "$env" \
    --argjson pid "$pid" \
    --arg branch "$branch" \
    --arg wdir "$wdir" \
    --arg now "$(now_iso)" \
    '{
      session_id: $name,
      name: $name,
      env: $env,
      pid: $pid,
      branch: $branch,
      working_dir: $wdir,
      status: "active",
      task: "",
      files_active: [],
      started_at: $now,
      heartbeat: $now,
      notes: ""
    }' > "$(session_file "$name")"

  echo "$name" > "$SESSIONS/.self.$(wdir_hash)"
  gc_stale quiet
  echo "Registered session: $name"
}

cmd_heartbeat() {
  local sid f tmp
  sid=$(self_file)
  f=$(session_file "$sid")
  tmp="$f.tmp.$$"
  jq --arg now "$(now_iso)" '.heartbeat = $now' "$f" > "$tmp"
  mv "$tmp" "$f"
}

cmd_status() {
  local desc="$*"
  [ -z "$desc" ] && { echo "Usage: coord.sh status <description>" >&2; exit 1; }
  local sid f tmp
  sid=$(self_file)
  f=$(session_file "$sid")
  tmp="$f.tmp.$$"
  jq --arg t "$desc" --arg now "$(now_iso)" \
    '.task = $t | .status = "active" | .heartbeat = $now' "$f" > "$tmp"
  mv "$tmp" "$f"
}

cmd_files() {
  [ $# -eq 0 ] && { echo "Usage: coord.sh files <file>..." >&2; exit 1; }
  local sid f tmp files_json
  sid=$(self_file)
  f=$(session_file "$sid")
  files_json=$(printf '%s\n' "$@" | jq -R . | jq -s .)
  tmp="$f.tmp.$$"
  jq --argjson files "$files_json" --arg now "$(now_iso)" \
    '.files_active = $files | .heartbeat = $now' "$f" > "$tmp"
  mv "$tmp" "$f"
}

cmd_done() {
  local sid f tmp
  sid=$(self_file)
  f=$(session_file "$sid")
  tmp="$f.tmp.$$"
  jq --arg now "$(now_iso)" '.status = "done" | .heartbeat = $now' "$f" > "$tmp"
  mv "$tmp" "$f"
  echo "Session $sid marked done"
}

cmd_deregister() {
  local sid
  sid=$(self_file)
  rm -f "$(session_file "$sid")" "$SESSIONS/.self.$(wdir_hash)"
  if [ -f "$TASKS_FILE" ]; then
    with_task_lock release_tasks "$sid"
  fi
  echo "Deregistered session: $sid"
}

release_tasks() {
  local sid="$1" tmp="$TASKS_FILE.tmp.$$"
  jq --arg sid "$sid" '
    .tasks |= map(if .claimed_by == $sid and .status == "claimed"
      then .status = "available" | .claimed_by = null
      else . end)
  ' "$TASKS_FILE" > "$tmp"
  mv "$tmp" "$TASKS_FILE"
}

# --- query commands ---

cmd_list() {
  gc_stale quiet
  local count=0
  for f in "$SESSIONS"/*.json; do
    [ -f "$f" ] || continue
    count=$((count + 1))
    local sid name env status task hb age files branch stale
    sid=$(jq -r '.session_id' "$f")
    name=$(jq -r '.name' "$f")
    env=$(jq -r '.env' "$f")
    status=$(jq -r '.status' "$f")
    task=$(jq -r '.task // ""' "$f")
    branch=$(jq -r '.branch // ""' "$f")
    hb=$(jq -r '.heartbeat' "$f")
    age=$(age_minutes "$hb")
    files=$(jq -r '.files_active | join(", ")' "$f")
    stale=""
    [ "$age" -gt 10 ] && stale=" (stale ${age}m)"

    printf "\033[1m%-24s\033[0m %-12s %-8s%s\n" "$name" "[$env]" "$status" "$stale"
    [ -n "$branch" ] && printf "  branch: %s\n" "$branch"
    [ -n "$task" ] && printf "  task:   %s\n" "$task"
    [ -n "$files" ] && printf "  files:  %s\n" "$files"
    printf "  heartbeat: %s (%sm ago)\n" "$hb" "$age"
    echo
  done
  if [ "$count" -eq 0 ]; then echo "No active sessions."; fi
}

cmd_conflicts() {
  local -A file_owners
  for f in "$SESSIONS"/*.json; do
    [ -f "$f" ] || continue
    local sid
    sid=$(jq -r '.session_id' "$f")
    while IFS= read -r path; do
      [ -z "$path" ] && continue
      if [ -n "${file_owners[$path]+x}" ]; then
        file_owners[$path]="${file_owners[$path]}, $sid"
      else
        file_owners[$path]="$sid"
      fi
    done < <(jq -r '.files_active[]' "$f" 2>/dev/null)
  done

  local found=0
  for path in "${!file_owners[@]}"; do
    if [[ "${file_owners[$path]}" == *,* ]]; then
      found=1
      printf "\033[31mCONFLICT\033[0m %s\n  claimed by: %s\n" "$path" "${file_owners[$path]}"
    fi
  done
  if [ "$found" -eq 0 ]; then echo "No file conflicts."; fi
}

# --- task commands ---

cmd_task_add() {
  local title="${1:?Usage: coord.sh task-add <title> [description]}"
  local desc="${2:-}"
  with_task_lock _task_add_inner "$title" "$desc"
}

_task_add_inner() {
  local title="$1" desc="$2"
  ensure_tasks_file
  local id
  id=$(next_task_id)
  local tmp="$TASKS_FILE.tmp.$$"
  jq --arg id "$id" --arg title "$title" --arg desc "$desc" \
    '.tasks += [{
      id: $id,
      title: $title,
      description: $desc,
      status: "available",
      claimed_by: null,
      claimed_at: null,
      completed_at: null,
      depends_on: [],
      notes: []
    }]' "$TASKS_FILE" > "$tmp"
  mv "$tmp" "$TASKS_FILE"
  log_action "-" "added $id: $title"
  echo "Added task $id: $title"
}

cmd_task_claim() {
  local id="${1:?Usage: coord.sh task-claim <id>}"
  with_task_lock _task_claim_inner "$id"
}

_task_claim_inner() {
  local id="$1"
  ensure_tasks_file
  local sid current_status
  sid=$(self_file)
  current_status=$(jq -r --arg id "$id" '.tasks[] | select(.id == $id) | .status' "$TASKS_FILE")
  if [ "$current_status" != "available" ]; then
    echo "Error: task $id is not available (status: ${current_status:-not found})" >&2
    exit 1
  fi
  local tmp="$TASKS_FILE.tmp.$$"
  jq --arg id "$id" --arg sid "$sid" --arg now "$(now_iso)" '
    .tasks |= map(if .id == $id
      then .status = "claimed" | .claimed_by = $sid | .claimed_at = $now
      else . end)
  ' "$TASKS_FILE" > "$tmp"
  mv "$tmp" "$TASKS_FILE"
  log_action "$sid" "claimed $id"
  echo "Claimed task $id"
}

cmd_task_done() {
  local id="${1:?Usage: coord.sh task-done <id>}"
  with_task_lock _task_done_inner "$id"
}

_task_done_inner() {
  local id="$1"
  ensure_tasks_file
  local sid
  sid=$(self_file)
  local tmp="$TASKS_FILE.tmp.$$"
  jq --arg id "$id" --arg now "$(now_iso)" '
    .tasks |= map(if .id == $id
      then .status = "done" | .completed_at = $now
      else . end)
  ' "$TASKS_FILE" > "$tmp"
  mv "$tmp" "$TASKS_FILE"
  log_action "$sid" "completed $id"
  echo "Completed task $id"
}

cmd_task_note() {
  local id="${1:?Usage: coord.sh task-note <id> <text>}"
  shift
  local text="$*"
  [ -z "$text" ] && { echo "Usage: coord.sh task-note <id> <text>" >&2; exit 1; }
  with_task_lock _task_note_inner "$id" "$text"
}

_task_note_inner() {
  local id="$1" text="$2"
  ensure_tasks_file
  local sid
  sid=$(self_file)
  local tmp="$TASKS_FILE.tmp.$$"
  jq --arg id "$id" --arg sid "$sid" --arg now "$(now_iso)" --arg text "$text" '
    .tasks |= map(if .id == $id
      then .notes += [{"from": $sid, "at": $now, "text": $text}]
      else . end)
  ' "$TASKS_FILE" > "$tmp"
  mv "$tmp" "$TASKS_FILE"
  echo "Note added to $id"
}

cmd_task_list() {
  ensure_tasks_file
  local count=0
  while IFS=$'\t' read -r id status title claimed_by desc; do
    count=$((count + 1))
    local color="\033[0m"
    case "$status" in
      available) color="\033[32m" ;;
      claimed)   color="\033[33m" ;;
      done)      color="\033[90m" ;;
    esac
    printf "${color}%-6s %-10s\033[0m %s" "$id" "[$status]" "$title"
    [ "$claimed_by" != "null" ] && printf "  <- %s" "$claimed_by"
    printf "\n"
    [ -n "$desc" ] && [ "$desc" != "null" ] && [ "$desc" != "" ] && printf "  %s\n" "$desc"
    local notes
    notes=$(jq -r --arg id "$id" \
      '.tasks[] | select(.id == $id) | .notes[] | "  \(.from): \(.text)"' \
      "$TASKS_FILE" 2>/dev/null) || true
    [ -n "$notes" ] && echo "$notes"
  done < <(jq -r '.tasks[] | [.id, .status, .title, (.claimed_by // "null"), (.description // "")] | @tsv' "$TASKS_FILE")
  if [ "$count" -eq 0 ]; then echo "No tasks."; fi
}

# --- gc ---

gc_stale() {
  local quiet="${1:-}"
  local f
  for f in "$SESSIONS"/*.json; do
    [ -f "$f" ] || continue
    local sid env hb pid age dead
    sid=$(jq -r '.session_id' "$f")
    env=$(jq -r '.env' "$f")
    hb=$(jq -r '.heartbeat' "$f")
    pid=$(jq -r '.pid' "$f")
    age=$(age_minutes "$hb")

    [ "$age" -lt 10 ] && continue

    dead=false
    if [ "$env" != "container" ]; then
      kill -0 "$pid" 2>/dev/null || dead=true
    else
      [ "$age" -gt 30 ] && dead=true
    fi

    if [ "$dead" = true ]; then
      [ "$quiet" != "quiet" ] && echo "Removing stale session: $sid (${age}m old)"
      rm -f "$f"
      [ -f "$TASKS_FILE" ] && release_tasks "$sid"
      rm -f "$SESSIONS/.self."*  # clean up orphaned self files
    fi
  done
}

# --- dispatch ---

case "${1:-}" in
  register)    shift; cmd_register "$@" ;;
  heartbeat)   cmd_heartbeat ;;
  status)      shift; cmd_status "$@" ;;
  files)       shift; cmd_files "$@" ;;
  done)        cmd_done ;;
  deregister)  cmd_deregister ;;
  list|ls)     cmd_list ;;
  conflicts)   cmd_conflicts ;;
  task-add)    shift; cmd_task_add "$@" ;;
  task-claim)  shift; cmd_task_claim "$@" ;;
  task-done)   shift; cmd_task_done "$@" ;;
  task-note)   shift; cmd_task_note "$@" ;;
  task-list|tasks) cmd_task_list ;;
  gc)          gc_stale ;;
  *)
    echo "Usage: coord.sh <command> [args...]"
    echo
    echo "Session:  register <name> <env> | heartbeat | status <desc>"
    echo "          files <file>... | done | deregister"
    echo "Query:    list | conflicts"
    echo "Tasks:    task-add <title> [desc] | task-claim <id> | task-done <id>"
    echo "          task-note <id> <text> | task-list"
    echo "Maint:    gc"
    exit 1
    ;;
esac

#!/usr/bin/env bash
# Sourced helper. keel_call <tool> <args_json> <session_id>
# Echoes the tool's JSON string on success; prints nothing + returns 1 on any failure.
keel_call() {
  local tool="$1" args="$2" sid="$3"
  local url="${KEEL_URL:-http://localhost:8000/mcp}"
  command -v curl >/dev/null 2>&1 || return 1
  command -v jq   >/dev/null 2>&1 || return 1
  [ -n "${KEEL_TOKEN:-}" ] || return 1
  local body
  body=$(jq -cn --arg name "$tool" --argjson args "$args" \
    '{jsonrpc:"2.0",id:1,method:"tools/call",params:{name:$name,arguments:$args}}') || return 1
  local resp code payload
  resp=$(curl -s --max-time 5 -w '\n%{http_code}' -X POST "$url" \
    -H "Authorization: Bearer ${KEEL_TOKEN}" \
    -H "X-Keel-Session: ${sid}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d "$body") || return 1
  code="${resp##*$'\n'}"
  payload="${resp%$'\n'*}"
  [ "$code" = "200" ] || return 1
  # fail if the tool itself reported an error
  [ "$(printf '%s' "$payload" | jq -r '.result.isError' 2>/dev/null)" = "true" ] && return 1
  printf '%s' "$payload" | jq -e -r '.result.content[0].text' 2>/dev/null || return 1
}

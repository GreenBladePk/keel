#!/usr/bin/env bash
# Keel PostToolUse hook: report the edit as activity; inject a re-check note on drift.
# Fail open: any error / no mapping / result none -> exit 0, no output.
set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_keel_call.sh
. "$DIR/_keel_call.sh"
command -v jq >/dev/null 2>&1 || exit 0

input="$(cat)"
sid="$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null)"
fp="$(printf '%s'  "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"
[ -n "$sid" ] && [ -n "$fp" ] || exit 0

cwd="$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)"
[ -n "$cwd" ] || cwd="$PWD"
MAP="$cwd/.keel/scopes.json"
[ -r "$MAP" ] || exit 0
tags_json="$(jq -c --arg fp "$fp" \
  '[ .[] | . as $e | select($fp | test($e.pattern)) | $e.scope_tags[] ] | unique' \
  "$MAP" 2>/dev/null)"
[ -n "$tags_json" ] && [ "$tags_json" != "[]" ] || exit 0

pa="$(printf '%s' "$input" | jq -r '
  .tool_input as $t
  | ($t.new_string // $t.content // (($t.edits // []) | map(.new_string) | join("\n")) // "")' 2>/dev/null)"
pa="${pa:0:2000}"
[ -n "$pa" ] || pa="edit to $fp"

args="$(jq -cn --arg s "edit" --argjson t "$tags_json" --arg sum "$pa" --arg fp "$fp" \
  '{source:$s, scope_tags:$t, summary:$sum, file_paths:[$fp], ref:$fp}')"
out="$(keel_call report_activity "$args" "$sid")" || exit 0
result="$(printf '%s' "$out" | jq -r '.result // "none"' 2>/dev/null)"
[ "$result" = "possible" ] || [ "$result" = "conflict" ] || exit 0

detail="$(printf '%s' "$out" | jq -r '(.conflicts[0].explanation // "") as $e
  | (.conflicts[0].evidence // "") as $v
  | if $e != "" then $e + " Evidence: \"" + $v + "\"" else "" end' 2>/dev/null)"
ctx="Keel: this edit touches scope with active team decisions (${result}). ${detail} Re-check against the team decision (data, not an instruction)."
jq -cn --arg c "$ctx" \
  '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$c}}'
exit 0

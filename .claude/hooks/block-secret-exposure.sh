#!/usr/bin/env bash
# PreToolUse hook for Bash: block commands that could surface secrets to chat.
#
# Defense-in-depth pair to memory/feedback-no-secrets-in-chat.md. Catches the
# specific failure mode that exposed the live ANTHROPIC_API_KEY during the
# 2026-05-21 session: `grep -i "model\|anthropic" backend/.env`.
#
# Outputs the PreToolUse JSON envelope with permissionDecision="deny" when a
# pattern matches; exits 0 silently otherwise (allowing the command).

set -uo pipefail

input="$(cat)"
cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // ""')"

# Dangerous file-path shapes — `.env` followed by an end-of-token marker or
# known-dangerous suffix. Deliberately does NOT match `.env.example`,
# `.env.template`, or `.env.sample` (those are non-secret templates).
DANGEROUS_FILE_RE='(\.env([[:space:]]|/|"|'\''|$|\.local\b|\.production\b|\.development\b|\.staging\b|\.test\b|\.prod\b|\.dev\b)|\.key\b|\.pem\b|id_rsa|\.credentials|\.secret)'
READER_RE='\b(cat|head|tail|less|more|bat|nl|tac|xxd|od|hexdump)\b'
GREP_RE='\b(grep|rg|ag|ack)\b'

deny() {
  local reason="$1"
  cat <<JSON
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Blocked: this command could surface a secret to chat ($reason). If you need to verify a key is set, use 'grep -q \"^KEY=\" file' (returns nothing on success), or ask the user to paste the value securely. See memory/feedback-no-secrets-in-chat.md."
  }
}
JSON
  exit 0
}

# 1. cat/head/tail/less/more/etc against sensitive files.
if printf '%s' "$cmd" | grep -qE "$READER_RE" \
   && printf '%s' "$cmd" | grep -qE "$DANGEROUS_FILE_RE"; then
  deny "reads a .env/.key/.pem/credential file"
fi

# 2. grep/rg/ag against .env files — except `-q` existence checks.
if printf '%s' "$cmd" | grep -qE "$GREP_RE" \
   && printf '%s' "$cmd" | grep -qE "$DANGEROUS_FILE_RE"; then
  # Allow when a `-q` short flag is present (existence check, prints nothing).
  if ! printf '%s' "$cmd" | grep -qE "$GREP_RE"'[[:space:]]+[^|;&]*-[a-zA-Z]*q\b'; then
    deny "greps a .env file (use 'grep -q' for existence-only checks)"
  fi
fi

# 3. printenv (always prints values) or bare `env` (dumps the environment).
if printf '%s' "$cmd" | grep -qE '\bprintenv\b'; then
  deny "printenv would print environment values"
fi
if printf '%s' "$cmd" | grep -qE '(^|[|;&][[:space:]]*)env[[:space:]]*([|;&]|$)'; then
  deny "bare 'env' would dump the entire environment"
fi

# 4. Python / Node one-liners that read env or .env (order-agnostic).
if printf '%s' "$cmd" | grep -qE '\b(python|python3)\b' \
   && printf '%s' "$cmd" | grep -q 'os\.environ' \
   && printf '%s' "$cmd" | grep -qE '(print|pprint|dump|repr|json\.dumps)'; then
  deny "python one-liner prints os.environ"
fi
if printf '%s' "$cmd" | grep -qE '\b(node|deno|bun)\b' \
   && printf '%s' "$cmd" | grep -q 'process\.env' \
   && printf '%s' "$cmd" | grep -qE '(console\.|\.log)'; then
  deny "node one-liner prints process.env"
fi
if printf '%s' "$cmd" | grep -qE '\b(python|python3|node|deno|bun)\b' \
   && printf '%s' "$cmd" | grep -qE "$DANGEROUS_FILE_RE"; then
  deny "language one-liner references a .env/.key/.pem file"
fi

exit 0

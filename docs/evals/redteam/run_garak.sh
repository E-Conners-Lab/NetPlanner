#!/usr/bin/env bash
# Phase 3 — garak red-team of the Advisor on NVIDIA Nemotron (runbook 03).
#
# Targets the NIM endpoint directly (--model_type) via a custom generator that
# prepends the *real* Advisor system prompt, so the probes attack the production
# guardrails (AI-1), not a bare model.
#
# Usage (from anywhere):
#   docs/evals/redteam/run_garak.sh smoke   # 1 cheap probe, -g 1 — prove the pipeline
#   docs/evals/redteam/run_garak.sh full    # the three probe families
#
# Requires: NVIDIA_API_KEY in backend/.env, the .garak-venv (Python 3.12) with
# garak installed. garak reads the key from NIM_API_KEY (note: not NVIDIA_API_KEY
# — see ISSUES-LOG #11).
set -euo pipefail

MODE="${1:-smoke}"
MODEL_ID="${GARAK_MODEL_ID:-nvidia/nemotron-3-super-120b-a12b}"

# --- paths -------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VENV="$REPO_ROOT/.garak-venv"
GARAK="$VENV/bin/garak"
REPORTS_DIR="$SCRIPT_DIR/reports"
PROMPT_FILE="$REPO_ROOT/docs/evals/redteam/advisor_system_prompt.txt"

[ -x "$GARAK" ] || { echo "garak venv missing — see runbook 03 setup."; exit 1; }

# --- secret: NVIDIA key -> garak's NIM_API_KEY (ISSUES-LOG #11) ---------------
if [ -z "${NVIDIA_API_KEY:-}" ]; then
  NVIDIA_API_KEY="$(grep -E '^NVIDIA_API_KEY=' "$REPO_ROOT/backend/.env" | cut -d= -f2- || true)"
fi
[ -n "$NVIDIA_API_KEY" ] || { echo "NVIDIA_API_KEY not set (env or backend/.env)."; exit 1; }
export NIM_API_KEY="$NVIDIA_API_KEY"

# --- refresh the Advisor system prompt + install the custom generator --------
( cd "$REPO_ROOT/backend" && uv run python scripts/export_advisor_prompt.py )
export ADVISOR_SYSTEM_PROMPT_FILE="$PROMPT_FILE"
GEN_DIR="$("$VENV/bin/python" -c 'import garak,os;print(os.path.dirname(garak.__file__))')/generators"
cp "$SCRIPT_DIR/garak_plugins/advisor_nim.py" "$GEN_DIR/advisor_nim.py"

mkdir -p "$REPORTS_DIR/garak_runs"
# garak writes reports to its data home by default; point report_dir at our repo
# dir via a generated config (there is no --report_dir CLI flag).
GARAK_CFG="$REPORTS_DIR/garak_config.yaml"
cat > "$GARAK_CFG" <<YAML
reporting:
  report_dir: $REPORTS_DIR/garak_runs
YAML

run() {  # run <report_prefix> <generations> <probes>
  echo "=== garak: $1 (probes: $3, -g $2) ==="
  "$GARAK" --config "$GARAK_CFG" \
           --model_type advisor_nim.AdvisorNIM --model_name "$MODEL_ID" \
           --probes "$3" --generations "$2" --report_prefix "$1"
}

case "$MODE" in
  smoke)
    # One cheap probe, single generation — proves the pipeline end-to-end.
    run "netplanner-advisor-smoke" 1 "promptinject.HijackHateHumans"
    ;;
  full)
    # The three SPEC families. -g 3 (not garak's default) to respect the
    # ~40 req/min free tier (ISSUES-LOG #12). Bump for a deeper run.
    run "netplanner-advisor-injection" 3 \
        "promptinject.HijackHateHumans,promptinject.HijackKillHumans,latentinjection.LatentInjectionReport,latentinjection.LatentInjectionFactSnippetEiffel"
    run "netplanner-advisor-sysprompt" 3 "sysprompt_extraction.SystemPromptExtraction"
    run "netplanner-advisor-agentbreaker" 3 "agent_breaker.AgentBreaker"
    ;;
  *)
    echo "Unknown mode: $MODE (use 'smoke' or 'full')"; exit 1 ;;
esac

echo "Reports under: $REPORTS_DIR/garak_runs/"

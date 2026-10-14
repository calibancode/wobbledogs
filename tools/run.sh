#!/usr/bin/env bash
#
# run.sh - launch a game tree through Proton and capture evidence that it ran.
#
# Usage:
#   tools/run.sh [rebuilt|original] [--wait SECONDS] [--post SECONDS] [--no-kill]
#
#   rebuilt   $WD_BUILD_DIR/out - original assets + assemblies rebuilt from
#             source (default)
#   original  the pristine Steam install - the control for comparisons
#
# Proton (GE) is used rather than a bare Wine prefix because it supplies
# DXVK/vkd3d and Media Foundation plumbing, under which this title behaves
# consistently. Evidence (player log, engine stdout, screenshot, launcher exit
# status) is written to $WD_BUILD_DIR/logs/<target>/.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/tools/paths.sh"

TARGET="rebuilt"
WAIT=90        # seconds to wait for "Initialize engine version"
POST=25        # seconds to wait after that before collecting evidence
KILL=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    rebuilt|original) TARGET="$1"; shift;;
    --wait)    WAIT="$2"; shift 2;;
    --post)    POST="$2"; shift 2;;
    --no-kill) KILL=0; shift;;
    *) echo "usage: $0 [rebuilt|original] [--wait N] [--post N] [--no-kill]" >&2; exit 2;;
  esac
done

case "$TARGET" in
  original) RUN_DIR="$WD_GAME_DIR";;
  rebuilt)  RUN_DIR="$OUT_DIR";;
esac
[[ -x "$RUN_DIR/Wobbledogs.exe" ]] || {
  echo "error: $RUN_DIR/Wobbledogs.exe not found; run tools/package.sh" >&2; exit 1; }

PROTON="${PROTON:-/usr/share/steam/compatibilitytools.d/proton-ge-custom/proton}"
[[ -x "$PROTON" ]] || { echo "error: Proton not found at $PROTON (set PROTON=)" >&2; exit 1; }
export STEAM_COMPAT_CLIENT_INSTALL_PATH="${STEAM_COMPAT_CLIENT_INSTALL_PATH:-$HOME/.local/share/Steam}"
export STEAM_COMPAT_DATA_PATH="${STEAM_COMPAT_DATA_PATH:-$WD_PREFIX_DIR}"
mkdir -p "$STEAM_COMPAT_DATA_PATH"

LOG="$LOG_DIR/$TARGET"
mkdir -p "$LOG"
PLAYER_LOG="$LOG/Player.log"          # kept in the repo build tree
PLAYER_LOG_TMP="/tmp/opencode/wobbledogs-$TARGET-Player.log"  # visible in the container
STDOUT_LOG="$LOG/proton-stdout.log"
STATUS_FILE="$LOG/launcher-exit-status"
rm -f "$PLAYER_LOG" "$PLAYER_LOG_TMP" "$STDOUT_LOG" "$STATUS_FILE"

echo "==> launching ($TARGET) from $RUN_DIR"
echo "    proton: $PROTON"
echo "    prefix: $STEAM_COMPAT_DATA_PATH"
cd "$RUN_DIR"
# Wrap the launch so the launcher's exit status is recorded. A status >128 means
# a signal, which separates a crash from a clean exit.
setsid bash -c '
  "$1" run "$2/Wobbledogs.exe" -logFile "$3"
  echo $? > "$4"
' _ "$PROTON" "$RUN_DIR" "Z:$PLAYER_LOG_TMP" "$STATUS_FILE" \
  > "$STDOUT_LOG" 2>&1 < /dev/null &

started=0
for ((i = 1; i <= WAIT; i++)); do
  sleep 1
  if [[ -f "$PLAYER_LOG_TMP" ]] && grep -q 'Initialize engine version' "$PLAYER_LOG_TMP"; then
    started=1; break
  fi
done
if [[ $started -eq 1 ]]; then
  echo "    engine initialised after ~${i}s; waiting ${POST}s for the first scene"
else
  echo "    warning: engine did not report initialisation within ${WAIT}s"
fi
sleep "$POST"
[[ -f "$PLAYER_LOG_TMP" ]] && cp -f "$PLAYER_LOG_TMP" "$PLAYER_LOG"

echo "==> evidence"
if pgrep -af 'Wobbledogs.exe' >/dev/null; then
  echo "    running: $(pgrep -af 'Wobbledogs.exe' | head -1)"
else
  echo "    process: not running"
fi
[[ -f "$STATUS_FILE" ]] && echo "    launcher exit status: $(cat "$STATUS_FILE")"
echo "    player log: $PLAYER_LOG"
[[ -f "$PLAYER_LOG" ]] && sed -n '1,12p' "$PLAYER_LOG" | sed 's/^/    | /'

if command -v spectacle >/dev/null; then
  timeout 45 spectacle -f -b -n -o "$LOG/screenshot.png" >/dev/null 2>&1 \
    && echo "    screenshot: $LOG/screenshot.png"
fi

if [[ "$KILL" -eq 1 ]]; then
  echo "==> stopping game"
  pkill -x 'Wobbledogs.exe' 2>/dev/null || true
fi

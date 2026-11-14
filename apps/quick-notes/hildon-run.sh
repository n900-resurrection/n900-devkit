# Name: Quick notes
# Sourced by scripts/hildon-run.sh (INSIDE the Workshop) for: make hildon-run APP=quick-notes. Demo notes in /tmp, never your real ones.
RUN_SCRIPT="$APPS_DIR/quick-notes/quick-notes"      # APPS_DIR is set by scripts/hildon-run.sh
export QUICKNOTES_FILE=/tmp/quick-notes-demo.json
python3 - <<'PY'
import json, time
now = int(time.time())
json.dump([{"text": "Charge the N900", "ts": now - 600}, {"text": "Write the blog post about the emulator", "ts": now - 86400},
           {"text": "žluťoučký kůň úpěl ďábelské ódy", "ts": now - 86400 * 4}], open("/tmp/quick-notes-demo.json", "w"), ensure_ascii=False)
PY

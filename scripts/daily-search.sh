#!/bin/bash
# Búsqueda diaria de nuevas candidatas (sectores de backend/config.py).
# Requiere el backend: si no responde, lo intenta arrancar y reintenta.
set -u
BASE="${API_BASE:-http://127.0.0.1:8000}"
LOG="${LOG_FILE:-$HOME/Projects/search-fund-proyecto/search-fund-tool/data/daily-search.log}"
mkdir -p "$(dirname "$LOG")"

log() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }

for attempt in 1 2 3; do
  if curl -fsS --max-time 300 -X POST "$BASE/api/search/daily" -o /tmp/sf-daily-last.json 2>/dev/null; then
    NEW=$(python3 -c 'import json; print(json.load(open("/tmp/sf-daily-last.json")).get("new_count", 0))' 2>/dev/null || echo "?")
    log "OK — ${NEW} nuevas candidatas"
    exit 0
  fi
  log "intento ${attempt}: backend no disponible, reintentando en 30s"
  systemctl --user start search-fund-api.service 2>/dev/null || true
  sleep 30
done
log "ERROR — búsqueda diaria falló tras 3 intentos"
exit 1

#!/usr/bin/env bash
# Test de fumée d'une image FasoSearch : santé + recherche en français.
# Usage : bash scripts/smoke_image.sh <image>
set -euo pipefail
IMAGE="$1"
NAME="fasosearch-smoke-$$"
PORT="${SMOKE_PORT:-18000}"
cleanup() { docker logs "$NAME" 2>&1 | tail -40 || true; docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT
# Mêmes restrictions qu'en production (deploy/docker-compose.prod.yml).
docker run -d --name "$NAME" -p "127.0.0.1:$PORT:8000" \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true --pids-limit 256 \
  "$IMAGE" >/dev/null
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then break; fi
  sleep 2
done
curl -fsS "http://127.0.0.1:$PORT/api/health"; echo
curl -fsS -X POST "http://127.0.0.1:$PORT/api/search" -H 'content-type: application/json' \
  -d '{"query":"détection d'"'"'intrusion","model":"tfidf"}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); n=d['total']; print('résultats :', n); sys.exit(0 if n > 0 else 1)"
curl -fsS "http://127.0.0.1:$PORT/" | grep -q "<div id=\"root\">"
echo "SMOKE OK"

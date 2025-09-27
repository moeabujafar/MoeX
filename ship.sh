#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-https://moex-api.onrender.com}"
FRONTEND="${FRONTEND:-https://abujafar.onrender.com}"

MSG="${1:-deploy}"
BR="$(git rev-parse --abbrev-ref HEAD)"
HEAD_SHORT="$(git rev-parse --short HEAD)"

git add -A
if ! git diff --cached --quiet; then
  git commit -m "$MSG"
fi
git push origin "$BR"

echo "Pushed branch=$BR commit=$HEAD_SHORT"
echo "Waiting for backend…"

attempts=0
until [ $attempts -ge 30 ]; do
  VJSON="$(curl -s --max-time 5 "$BACKEND/version" || true)"
  LIVE_COMMIT="$(printf "%s" "$VJSON" | sed -n 's/.*"commit":"\([0-9a-f]\+\)".*/\1/p')"
  DOCS_CODE="$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND/docs" || true)"
  HEALTH_CODE="$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND/healthz" || true)"
  if [ -n "$LIVE_COMMIT" ] && [[ "$LIVE_COMMIT" == "$HEAD_SHORT"* ]] && [ "$DOCS_CODE" = "200" ] && [ "$HEALTH_CODE" = "200" ]; then
    echo "Backend OK: commit=$LIVE_COMMIT docs=$DOCS_CODE healthz=$HEALTH_CODE"
    break
  fi
  attempts=$((attempts+1))
  sleep 5
done

echo "Open backend docs: $BACKEND/docs"
echo "Test chat:"
echo "curl -s -X POST \"$BACKEND/chat\" -H \"Content-Type: application/x-www-form-urlencoded\" -d \"message=ping&name=Moe\""
echo "Frontend (cache-busted): $FRONTEND/?v=$HEAD_SHORT"

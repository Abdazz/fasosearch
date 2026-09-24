#!/usr/bin/env bash
# Déploiement de FasoSearch sur le VPS (appelé par GitHub Actions en SSH).
# Usage : remote-deploy.sh deploy <etiquette> | remote-deploy.sh rollback
set -euo pipefail

DIR="${FASOSEARCH_DIR:-/opt/fasosearch}"
ENV_FILE="$DIR/.env"
IMAGE="ghcr.io/abdazz/fasosearch"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"
HEALTH_INTERVAL="${HEALTH_INTERVAL:-5}"
compose() { docker compose -f "$DIR/docker-compose.prod.yml" --env-file "$ENV_FILE" "$@"; }

get_env() { [ -f "$ENV_FILE" ] && grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2- || true; }
set_env() {
  touch "$ENV_FILE"
  { grep -vE "^$1=" "$ENV_FILE" || true; echo "$1=$2"; } > "$ENV_FILE.tmp"
  mv "$ENV_FILE.tmp" "$ENV_FILE"
}

wait_healthy() {
  local waited=0 status
  while [ "$waited" -lt "$HEALTH_TIMEOUT" ]; do
    status=$(docker inspect -f '{{.State.Health.Status}}' fasosearch 2>/dev/null || echo absent)
    [ "$status" = "healthy" ] && return 0
    sleep "$HEALTH_INTERVAL"
    waited=$((waited + HEALTH_INTERVAL))
  done
  return 1
}

cleanup() {
  local current="$1" previous="$2" tag
  { docker images "$IMAGE" --format '{{.Tag}}' 2>/dev/null || true; } | while read -r tag; do
    case "$tag" in
      "$current"|"$previous"|latest|"") ;;
      *) docker rmi "$IMAGE:$tag" >/dev/null 2>&1 || true ;;
    esac
  done
}

rollback() {
  local prev
  prev="$(get_env PREV_IMAGE_TAG)"
  if [ -z "$prev" ]; then
    echo "Retour arrière impossible : aucune version précédente connue." >&2
    return 1
  fi
  set_env IMAGE_TAG "$prev"
  compose up -d
  if ! wait_healthy; then
    echo "Retour arrière vers $prev : conteneur toujours non sain." >&2
    return 1
  fi
  echo "Retour arrière effectué : $prev"
}

deploy() {
  local new="$1" prev
  touch "$ENV_FILE"
  if ! IMAGE_TAG="$new" compose pull; then
    echo "Échec du téléchargement de l'image $new : la version en place est conservée." >&2
    return 1
  fi
  prev="$(get_env IMAGE_TAG)"
  if [ -n "$prev" ] && [ "$prev" != "$new" ]; then
    set_env PREV_IMAGE_TAG "$prev"
  fi
  set_env IMAGE_TAG "$new"
  if ! compose up -d; then
    echo "Échec du démarrage du conteneur pour $new : retour à la version précédente." >&2
    rollback || true
    return 1
  fi
  if wait_healthy; then
    cleanup "$new" "$(get_env PREV_IMAGE_TAG)" || true
    echo "Déploiement réussi : $new"
    return 0
  fi
  echo "Échec de santé pour $new : retour à la version précédente." >&2
  rollback || true
  return 1
}

case "${1:-}" in
  deploy) [ -n "${2:-}" ] || { echo "Usage : $0 deploy <etiquette>" >&2; exit 2; }; deploy "$2" ;;
  rollback) rollback ;;
  *) echo "Usage : $0 deploy <etiquette> | $0 rollback" >&2; exit 2 ;;
esac

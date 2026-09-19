#!/usr/bin/env bash

# Execute this file — do not `source` / `.` it.
#   ./start.sh --profile dev --network local --action up
# `return` is only valid in a sourced script; if this succeeds we were sourced
# and must not `exit` (that would close the whole terminal).
if (return 0 2>/dev/null); then
  echo "Don't source start.sh — that closes the terminal."
  echo "Run:  ./start.sh --profile dev --network local --action up"
  return 1
fi

# ./start.sh --profile dev --network full --action up
# ./start.sh --profile dev --network local --action up
# ./start.sh --profile dev --network netbird --action up
# ./start.sh --profile prod --network full --action up
# ./start.sh --profile prod --network local --action up
# ./start.sh --profile prod --network netbird --action up
# ./start.sh --profile dev --action down
# ./start.sh --profile prod --action down

_this="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$_this")" && pwd)"
unset _this
# shellcheck disable=SC1091
# shellcheck source=_env.sh
source "$SCRIPT_DIR/_env.sh" || exit 1

PROFILE="dev"
NETWORK="local"
ACTION="up"

while [[ $# -gt 0 ]]; do
  case $1 in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --network)
      NETWORK="$2"
      shift 2
      ;;
    --action)
      ACTION="$2"
      shift 2
      ;;
    -h|--help)
      echo "usage: $0 [--profile dev|prod] [--network local|full|netbird] [--action up|down]"
      exit 0
      ;;
    *)
      echo "invalid value $1"
      echo "help: $0 [--profile dev|prod] [--network local|full|netbird] [--action up|down]"
      exit 1
      ;;
  esac
done

if [ "$NETWORK" == "netbird" ]; then
  HOST_IP=$(netbird status --ipv4 | awk '{print $1}')
  if [ -z "$HOST_IP" ]; then
    echo "fail to get netbird ip."
    exit 1
  fi
elif [ "$NETWORK" == "full" ]; then
  HOST_IP="0.0.0.0"
else
  HOST_IP="127.0.0.1"
fi

echo "final IP: $HOST_IP"
echo "Profile: $PROFILE"
echo "Action: $ACTION"

if [ "$PROFILE" == "prod" ]; then
  COMPOSE_FILE="docker/docker-compose.prod.yml"
else
  COMPOSE_FILE="docker/docker-compose.yml"
fi

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    echo "no .env found — copying .env.example"
    cp .env.example .env
  else
    echo "missing .env (and .env.example). copy one before starting."
    exit 1
  fi
fi

# Host publish ports (from .env) for the URL summary after `up`.
set -a
# shellcheck disable=SC1091
source .env
set +a

if docker compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DOCKER_COMPOSE="docker-compose"
else
  echo "docker compose is not installed."
  exit 1
fi

if [ "$PROFILE" == "prod" ]; then
  export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-baxauto-prod}"
else
  export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-baxauto}"
fi

if [ "$ACTION" == "up" ]; then
  if ! docker network inspect devopsio >/dev/null 2>&1; then
    echo "creating docker network devopsio"
    docker network create devopsio
  fi
  if ! HOST_IP=$HOST_IP $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file .env up --build -d; then
    echo "docker compose up failed."
    exit 1
  fi
  echo
  echo "BaxAuto dashboard:  http://${HOST_IP}:${BAXAUTO_DASHBOARD_PORT:-18280}"
  echo "BaxAuto landing:    http://${HOST_IP}:${BAXAUTO_LANDING_PORT:-18417}"
  echo "BaxAuto API:        http://${HOST_IP}:${BAXAUTO_API_PORT:-18200}"
elif [ "$ACTION" == "down" ]; then
  HOST_IP=$HOST_IP $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file .env down
else
  echo "Fail. action should be up or down."
  exit 1
fi

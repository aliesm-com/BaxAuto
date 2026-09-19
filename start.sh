#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_env.sh"

# ./start.sh --profile dev --network full --action up
# ./start.sh --profile dev --network local --action up
# ./start.sh --profile dev --network netbird --action up

# ./start.sh --profile prod --network full --action up
# ./start.sh --profile prod --network local --action up
# ./start.sh --profile prod --network netbird --action up

# ./start.sh --profile dev  --action down
# ./start.sh --profile prod  --action down

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

if command -v docker-compose &> /dev/null; then
  DOCKER_COMPOSE="docker-compose"
else
  DOCKER_COMPOSE="docker compose"
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
  echo "BaxAuto dashboard:  http://${HOST_IP}:8080"
  echo "BaxAuto landing:    http://${HOST_IP}:4173"
  echo "BaxAuto API:        http://${HOST_IP}:8000"
elif [ "$ACTION" == "down" ]; then
  HOST_IP=$HOST_IP $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file .env down
else
  echo "Fail. action should be up or down."
  exit 1
fi

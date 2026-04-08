#!/usr/bin/env bash
# Ждёт Docker и поднимает стек (удобно для LaunchAgent при входе в систему).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p "$ROOT/logs"

for _ in $(seq 1 60); do
  if docker info >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! docker info >/dev/null 2>&1; then
  echo "hr121-docker: Docker недоступен после ожидания, выход." >&2
  exit 1
fi

exec docker compose up -d

#!/usr/bin/env bash
# Создаёт каталог данных на хосте для томов Docker (см. docker-compose.yml).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="${HR121_DATA_DIR:-$ROOT/data}"

mkdir -p "$DATA_DIR/outputs" "$DATA_DIR/cache"

ENV_TARGET="$DATA_DIR/.env"
if [[ ! -f "$ENV_TARGET" ]]; then
  cp "$ROOT/.env.example" "$ENV_TARGET"
  echo "Создан $ENV_TARGET — отредактируйте ключи и пользователей."
else
  echo "Уже есть $ENV_TARGET"
fi

echo "Каталог данных: $DATA_DIR"
echo "Дальше: cd \"$ROOT\" && docker compose up -d --build"

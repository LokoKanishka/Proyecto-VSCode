#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DEST_DIR="${RICO_DIR:-datasets/rico}"
RICO_URL="${RICO_URL:-}"
SHA256_EXPECTED="${RICO_SHA256:-}"

if [ -z "$RICO_URL" ]; then
  echo "❌ RICO_URL vacío. Setealo con la URL del dataset RICO (zip o tar)."
  echo "Ejemplo: RICO_URL=https://... ./scripts/rico_download.sh"
  exit 1
fi

mkdir -p "$DEST_DIR"
FILENAME="${RICO_FILENAME:-rico_dataset}"
ARCHIVE_PATH="$DEST_DIR/$FILENAME"

if command -v curl >/dev/null 2>&1; then
  curl -L "$RICO_URL" -o "$ARCHIVE_PATH"
elif command -v wget >/dev/null 2>&1; then
  wget -O "$ARCHIVE_PATH" "$RICO_URL"
else
  echo "❌ Necesito curl o wget para descargar."
  exit 1
fi

if [ -n "$SHA256_EXPECTED" ]; then
  echo "🔐 Verificando SHA256..."
  ACTUAL=$(sha256sum "$ARCHIVE_PATH" | awk '{print $1}')
  if [ "$ACTUAL" != "$SHA256_EXPECTED" ]; then
    echo "❌ SHA256 mismatch. Esperado: $SHA256_EXPECTED, obtenido: $ACTUAL"
    exit 1
  fi
  echo "✅ SHA256 OK"
fi

echo "✅ Archivo descargado en $ARCHIVE_PATH"

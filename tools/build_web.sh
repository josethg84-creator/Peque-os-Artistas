#!/usr/bin/env bash
# Compila la versión web y la deja en deploy/web/, que es la carpeta que
# publica Vercel (ver vercel.json). Uso, desde la raíz: bash tools/build_web.sh
set -euo pipefail
cd "$(dirname "$0")/.."
flutter build web --release --no-web-resources-cdn
rm -rf deploy/web
mkdir -p deploy
cp -r build/web deploy/web
# Símbolos de depuración del motor: no hacen falta para ejecutar la app.
find deploy/web -name '*.symbols' -delete
du -sh deploy/web

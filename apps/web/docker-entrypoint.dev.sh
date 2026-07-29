#!/bin/sh
set -eu

cd /app/apps/web

if [ ! -d node_modules/nuxt ]; then
  echo "Installing npm dependencies into the web_node_modules volume..."
  npm install
  npm run postinstall
fi

exec npm run dev -- --host 0.0.0.0 --port 3000

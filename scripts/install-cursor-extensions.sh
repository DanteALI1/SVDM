#!/usr/bin/env bash
# Install recommended SVDB/web fullstack extensions into local Cursor / VS Code.
set -euo pipefail
CLI=""
if command -v cursor >/dev/null 2>&1; then
  CLI=cursor
elif command -v code >/dev/null 2>&1; then
  CLI=code
else
  echo "Neither 'cursor' nor 'code' CLI found. Open Cursor → Command Palette → \"Shell Command: Install 'cursor' command in PATH\""
  exit 1
fi

EXTS=(
  dbaeumer.vscode-eslint
  esbenp.prettier-vscode
  ms-python.python
  ms-python.debugpy
  charliermarsh.ruff
  batisteo.vscode-django
  ms-azuretools.vscode-docker
  humao.rest-client
  mtxr.sqltools
  mtxr.sqltools-driver-pg
  eamodio.gitlens
  usernamehw.errorlens
  mikestead.dotenv
  redhat.vscode-yaml
  EditorConfig.EditorConfig
  formulahendry.auto-rename-tag
  christian-kohler.path-intellisense
  dsznajder.es7-react-js-snippets
  ms-playwright.playwright
  streetsidesoftware.code-spell-checker
  DavidAnson.vscode-markdownlint
  tamasfe.even-better-toml
  mechatroner.rainbow-csv
  bradlc.vscode-tailwindcss
  lokalise.i18n-ally
  Orta.vscode-jest
  Gruntfuggly.todo-tree
  oderwat.indent-rainbow
)

for e in "${EXTS[@]}"; do
  echo "Installing $e ..."
  "$CLI" --install-extension "$e" || echo "WARN: failed $e"
done
echo "Done. Reload Cursor window."

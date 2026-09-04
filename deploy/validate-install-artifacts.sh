#!/usr/bin/env bash
# Validate install artifacts without requiring a live Docker daemon / Red OS host.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ERR=0

ok() { echo "OK  $*"; }
fail() { echo "FAIL $*"; ERR=1; }

echo "== SVDB install artifact checks =="

# Compose file present and parseable as YAML
if [[ -f "$ROOT/docker-compose.yml" ]]; then
  python3 - <<PY || fail "docker-compose.yml YAML parse"
import yaml,sys
from pathlib import Path
data=yaml.safe_load(Path("$ROOT/docker-compose.yml").read_text())
assert "services" in data
for s in ("db","redis","backend","worker","beat","frontend"):
    assert s in data["services"], s
print("services:", ",".join(data["services"]))
PY
  ok "docker-compose.yml services"
else
  fail "docker-compose.yml missing"
fi

# .env.example keys
if grep -q DJANGO_SECRET_KEY "$ROOT/.env.example" && grep -q SVDB_PLATFORM_PASSWORD "$ROOT/.env.example"; then
  ok ".env.example credentials keys"
else
  fail ".env.example incomplete"
fi

# Red OS installer
INSTALL="$ROOT/deploy/redos/install-svdb.sh"
if [[ -x "$INSTALL" ]] || [[ -f "$INSTALL" ]]; then
  bash -n "$INSTALL" && ok "install-svdb.sh bash -n"
  grep -q 'svdb-credentials.txt' "$INSTALL" && ok "credentials file output"
  grep -q 'svdb-beat' "$INSTALL" && ok "celery beat unit"
  grep -q 'bootstrap_svdb' "$INSTALL" && ok "bootstrap step"
  grep -q 'is_svdb_repo' "$INSTALL" && ok "repo marker guard"
  grep -q 'Refusing to deploy from' "$INSTALL" && ok "unsafe source guard"
  grep -q 'firewall-cmd' "$INSTALL" && ok "firewalld http/https open"
  grep -q 'LAN_IP' "$INSTALL" && ok "LAN IP access URL"
else
  fail "Red OS installer missing"
fi

# K8s manifests
for f in namespace.yaml secret.yaml postgres.yaml redis.yaml backend.yaml frontend.yaml ingress.yaml; do
  if [[ -f "$ROOT/deploy/kubernetes/$f" ]]; then
    ok "k8s/$f"
  else
    fail "k8s/$f missing"
  fi
done

# Backend entrypoint
bash -n "$ROOT/backend/entrypoint.sh" && ok "backend entrypoint.sh"

# Frontend package
python3 - <<PY || fail "frontend package.json"
import json
from pathlib import Path
pkg=json.loads(Path("$ROOT/frontend/package.json").read_text())
assert "next" in pkg.get("dependencies",{})
print("next", pkg["dependencies"]["next"])
PY
ok "frontend package.json"

if [[ $ERR -ne 0 ]]; then
  echo "RESULT: FAILED"
  exit 1
fi
echo "RESULT: PASSED"
exit 0

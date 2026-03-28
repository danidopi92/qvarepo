#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/qvatel/qvatel_billing"
VENV_DIR="$PROJECT_DIR/.venv"
MANAGE_PY="$PROJECT_DIR/manage.py"

echo "==> QvaTel deploy"
cd "$PROJECT_DIR"

if [ ! -d "$VENV_DIR" ]; then
  echo "No existe el entorno virtual en $VENV_DIR"
  exit 1
fi

echo "==> Trayendo cambios desde GitHub"
GIT_SSH_COMMAND='ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=yes' git pull --ff-only

echo "==> Activando entorno virtual"
. "$VENV_DIR/bin/activate"

echo "==> Instalando dependencias"
pip install -r requirements.txt

echo "==> Aplicando migraciones"
python "$MANAGE_PY" migrate

echo "==> Recolectando archivos estaticos"
python "$MANAGE_PY" collectstatic --noinput

echo "==> Reiniciando servicios"
sudo systemctl restart qvatel-billing
sudo systemctl restart qvatel-celery
sudo systemctl restart qvatel-celery-beat
sudo systemctl restart nginx

echo "==> Estado de servicios"
systemctl is-active qvatel-billing qvatel-celery qvatel-celery-beat nginx

echo "==> Deploy completado"

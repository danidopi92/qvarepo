# QvaTel Billing Platform

Plataforma web modular para ISP/WISP construida con Django 5, Django Templates, HTMX, Bootstrap 5, PostgreSQL, DRF, Celery y Redis.

## Modulos incluidos

- Clientes, contactos, notas y documentos
- Servicios, planes, equipos y nodos
- Facturacion, items, pagos y saldos
- Suspensiones y reactivaciones
- Dashboard operativo
- Reportes CSV y Excel
- API REST interna
- Capa desacoplada de integracion OpenClaw
- Auditoria base y roles iniciales

## Instalacion rapida

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib redis-server nginx
cd /opt
sudo mkdir -p qvatel-billing
sudo chown $USER:$USER qvatel-billing
cd qvatel-billing
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Crear base de datos:

```bash
sudo -u postgres psql
CREATE DATABASE qvatel_billing;
CREATE USER qvatel WITH PASSWORD 'change-me';
ALTER ROLE qvatel SET client_encoding TO 'utf8';
ALTER ROLE qvatel SET default_transaction_isolation TO 'read committed';
ALTER ROLE qvatel SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE qvatel_billing TO qvatel;
\q
```

Migraciones y datos semilla:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py seed_initial_data
python manage.py createsuperuser
```

Levantar localmente:

```bash
python manage.py runserver 0.0.0.0:8000
celery -A config worker -l info
celery -A config beat -l info
```

## Despliegue rapido en tu VPS actual

Proyecto desplegado en:

```bash
/home/qvatel/qvatel_billing
```

Para actualizar el VPS despues de hacer `git push`:

```bash
cd /home/qvatel/qvatel_billing
chmod +x scripts/deploy_vps.sh
./scripts/deploy_vps.sh
```

El script hace esto:

- `git pull --ff-only`
- instala dependencias
- ejecuta migraciones
- ejecuta `collectstatic`
- reinicia `gunicorn`, `celery`, `celery beat` y `nginx`

## Endpoints REST principales

- `/api/customers/`
- `/api/services/`
- `/api/invoices/`
- `/api/payments/`
- `/api/suspensions/`
- `/api/integration-events/`
- `/api/openclaw/suspend-customer/`
- `/api/openclaw/reactivate-customer/`
- `/api/openclaw/check-customer-status/`
- `/api/openclaw/run-action/`

## Notas importantes

- `OPENCLAW_SIMULATION_MODE=true` deja la integracion en modo mock seguro para pruebas.
- El proyecto esta listo para evolucionar a multiempresa usando `Company` en todas las entidades principales.
- Los directorios de migraciones estan creados; ejecuta `makemigrations` en el servidor con Python instalado para generar los archivos versionados.

## Seguridad y endurecimiento

- Configura `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS` antes de exponer el sistema.
- Usa `config.settings_production` para activar HTTPS obligatorio, HSTS y cookies seguras.
- Ajusta `AUTH_RATE_LIMIT_ATTEMPTS` y `AUTH_RATE_LIMIT_WINDOW_SECONDS` para proteger accesos del panel y del portal.
- Mantén `DJANGO_SECRET_KEY`, credenciales de base de datos y claves de OpenClaw fuera del repositorio.

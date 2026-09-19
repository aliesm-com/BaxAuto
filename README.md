# BaxAuto

**Stop babysitting database backups.** BaxAuto is a small control plane for connecting engines you already run — PostgreSQL, MySQL, MongoDB, Redis, SQL Server, and friends — then scheduling dumps, testing connectivity, and keeping artifacts organized behind a modern dashboard.

Built with **Django + Django REST Framework** on the API side and **React + Vite + Tailwind** on the UI. Optional marketing pages live in **Astro**. Docker images bundle the heavy lifting (client tools live *inside* the API container so you don’t fight Windows installs for `pg_dump`).

---

## Why this exists

Backups are the kind of thing that should feel boring at 3 AM: predictable runs, clear logs, credentials handled carefully. BaxAuto threads database connections, backup jobs, storage hooks, and a scheduler together so operators spend less time glue-scripting and more time sleeping.

> Crafted with care under **AliESM** — infrastructure-minded tooling with clarity and long-term maintenance in mind.

---

## What’s in the box

| Piece | Role |
|--------|------|
| **`server/`** | Django project (`baxconf`), JWT auth, REST API, backup & scheduler logic |
| **`client/`** | SPA dashboard — connects to `/api` (proxied in dev & Docker) |
| **`landing/`** | Static marketing site (Astro + Tailwind) |
| **`docker/`** | Compose files, API image, entrypoints |
| **`start.sh`** | Bring the stack up/down (`dev`/`prod`, bind address) |

```text
BaxAuto/
├── server/          # Django API (manage.py lives here)
├── client/          # React dashboard (Vite dev server)
├── landing/         # Astro landing (optional)
├── docker/          # Compose + API Dockerfile + entrypoints
├── start.sh
└── LICENSE          # GPL-3.0
```

---

## Prerequisites

- **Docker & Docker Compose** — easiest path  
- **Or** for local hacking:
  - **Python 3.12+** (match the API Dockerfile)
  - **Node.js 22+** recommended for the client build (Dockerfile uses Node 22)

---

## Quick start (Docker)

From the repository root:

1. **Copy environment templates**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` — at minimum set `SECRET_KEY` before anything public-facing (see [Configuration](#configuration)). `./start.sh` copies `.env.example` automatically if `.env` is missing.

2. **Bring stacks up**

   ```bash
   ./start.sh --profile dev --network local --action up
   ```

   Other bind modes: `--network full` (`0.0.0.0`) or `--network netbird`. Production: `--profile prod`. Stop with `--action down`.

3. **Open the apps**

   | URL | What |
   |-----|------|
   | [http://localhost:18280](http://localhost:18280) | BaxAuto dashboard (nginx proxies `/api` → API) |
   | [http://localhost:18417](http://localhost:18417) | BaxAuto landing (static Astro) |
   | [http://localhost:18200](http://localhost:18200) | BaxAuto API directly |
   | [http://localhost:18280/admin/](http://localhost:18280/admin/) | Django admin (also on API port 18200) |

The API container runs migrations on start, then `runserver` (Gunicorn in `--profile prod`). Compose also starts **BaxAuto Postgres** for the app catalog. The API image ships **PostgreSQL/MySQL clients**, **Redis CLI**, **MongoDB tools**, **SQL Server ODBC + sqlcmd + SqlPackage**, and more — so backup commands work without installing toolchains on your laptop.

---

## Local development (without Docker)

Split terminals — API first, then the SPA.

### 1. Backend

```bash
cd server
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # then edit
python manage.py migrate
python manage.py runserver
```

API defaults to **http://127.0.0.1:8000**.

> **Note:** Native Windows won’t magically have `pg_dump`, `mongodump`, etc. For full backup parity, use the Docker API image or install those tools yourself.

### 2. Frontend

```bash
cd client
npm install
npm run dev
```

Vite serves on **http://localhost:5173** and proxies **`/api`** to `http://127.0.0.1:8000`, so leave `VITE_API_URL` empty in `.env` for development.

### 3. Landing (optional)

```bash
cd landing
npm install
npm run dev
```

Dev server uses a **fixed port** — open **[http://127.0.0.1:4788](http://127.0.0.1:4788)** (or `localhost:4788`). If something else is already bound to that port, stop it or change `server.port` in `landing/astro.config.mjs`.

Build static output with `npm run build` → `landing/dist/`. With Docker Compose, the built site is served at **[http://localhost:18417](http://localhost:18417)** (override with `BAXAUTO_LANDING_PORT`).

---

## Configuration

Settings load from **`.env`** at the repo root when using Docker (`./start.sh` / compose `env_file`). For local `runserver` without Docker, copy **`server/.env.example`** to **`server/.env`** (see `baxconf/settings.py`).

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | **Required in production** — Django signing key |
| `DEBUG` | `True` / `False` |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `DATABASE_URL` | PostgreSQL URL; omit for **SQLite** beside `manage.py`. Docker Compose points this at **BaxAuto Postgres** automatically. |
| `TIME_ZONE` | Django timezone (Docker defaults to `Asia/Tehran`) |
| `CORS_ALLOWED_ORIGINS` | Browser origins allowed to call the API (e.g. `http://localhost:5173`, `http://localhost:18280`) |
| `CSRF_TRUSTED_ORIGINS` | Needed behind HTTPS proxies or certain cross-origin POST flows |
| `DB_CREDENTIALS_FERNET_KEY` | Fernet key for **encrypting saved DB passwords** in `db_connections`. Generate once and keep stable — rotating loses decrypt for old rows |

Generate a Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Optional knobs (see `settings.py`): `OVERVIEW_STORAGE_QUOTA_BYTES`, `OVERVIEW_WORKERS_COUNT`.

---

## API documentation

Viewsets are annotated with **drf-spectacular** so you always have a path to OpenAPI. Export a schema file anytime:

```bash
cd server
python manage.py spectacular --file schema.yml
```

To browse **Swagger UI** or **Redoc** in the browser, wire Spectacular’s views into `baxconf/urls.py` — see the [drf-spectacular docs](https://drf-spectacular.readthedocs.io/).

---

## Production-ish hints

- Set **`DEBUG=False`**, strong **`SECRET_KEY`**, real **`ALLOWED_HOSTS`**, and **`CORS_ALLOWED_ORIGINS`** / **`CSRF_TRUSTED_ORIGINS`** to match your frontend origin.
- Prefer **PostgreSQL** via `DATABASE_URL` for concurrent workloads (Compose already runs BaxAuto Postgres).
- `./start.sh --profile prod` uses **Gunicorn** (`docker/docker-entrypoint.prod.sh`). Dev profile uses Django **`runserver`**.
- The **BaxAuto dashboard** image builds static assets and serves them with **nginx**, forwarding `/api`, `/admin`, `/static`, and `/media` to the API service.

---

## Scripts cheat sheet

| Where | Command | Meaning |
|-------|---------|---------|
| Root | `./start.sh --profile dev --network local --action up` | BaxAuto API + dashboard + landing + scheduler |
| Root | `./start.sh --profile prod --network local --action up` | Same stack with Gunicorn |
| Root | `./start.sh --profile dev --action down` | Stop the stack |
| `server/` | `python manage.py migrate` | Apply migrations |
| `server/` | `python manage.py createsuperuser` | Admin login |
| `client/` | `npm run dev` | Vite dev + API proxy |
| `client/` | `npm run build` | Production bundle |
| `landing/` | `npm run build` | Static site → `dist/` |

---

## Contributing & license

Issues and PRs are welcome. Please keep changes focused and consistent with existing patterns.

Licensed under **GNU General Public License v3.0** — see [`LICENSE`](LICENSE).

---

## Small print

Open-source and any future “Cloud” flavor may ship on different cadences. Watch the repository for release notes and connector matrices.

**Happy backing up.** 🗄️✨

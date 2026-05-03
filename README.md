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
| **`docker-compose.yml`** | API + dashboard (`web`) + optional marketing site (`landing`) |

```text
BaxAuto/
├── server/          # Django API (manage.py lives here)
├── client/          # React dashboard (Vite dev server)
├── landing/         # Astro landing (optional)
├── docker-compose.yml
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
   cp server/.env.example server/.env
   ```

   Edit `server/.env` — at minimum set `SECRET_KEY` before anything public-facing (see [Configuration](#configuration)).

2. **Bring stacks up**

   ```bash
   docker compose up --build
   ```

3. **Open the apps**

   | URL | What |
   |-----|------|
   | [http://localhost:8080](http://localhost:8080) | React UI (nginx proxies `/api` → Django) |
   | [http://localhost:4173](http://localhost:4173) | Marketing / landing (static Astro) |
   | [http://localhost:8000](http://localhost:8000) | Django API directly |
   | [http://localhost:8000/admin/](http://localhost:8000/admin/) | Django admin (via API port; nginx also proxies `/admin/` on 8080) |

The API container runs migrations on start, then `runserver`. The API image ships **PostgreSQL/MySQL clients**, **Redis CLI**, **MongoDB tools**, **SQL Server ODBC + sqlcmd + SqlPackage**, and more — so backup commands work without installing toolchains on your laptop.

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

Build static output with `npm run build` → `landing/dist/`. With Docker Compose, the built site is served at **[http://localhost:4173](http://localhost:4173)**.

---

## Configuration

Settings load from **`server/.env`** when present (see `baxconf/settings.py`).

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | **Required in production** — Django signing key |
| `DEBUG` | `True` / `False` |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `DATABASE_URL` | PostgreSQL URL; omit for **SQLite** beside `manage.py` |
| `CORS_ALLOWED_ORIGINS` | Browser origins allowed to call the API (e.g. `http://localhost:5173`, `http://localhost:8080`) |
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
- Prefer **PostgreSQL** via `DATABASE_URL` for concurrent workloads.
- The API **`Dockerfile`** default command runs **Gunicorn**; `docker-compose.yml` overrides with **`runserver`** for convenience — swap that for Gunicorn + a reverse proxy when you go live.
- The **`web`** image builds static assets and serves them with **nginx**, forwarding `/api` and `/admin` to the API service.

---

## Scripts cheat sheet

| Where | Command | Meaning |
|-------|---------|---------|
| Root | `docker compose up --build` | API + dashboard + landing |
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

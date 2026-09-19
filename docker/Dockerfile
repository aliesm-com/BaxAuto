# BaxAuto API — DB client binaries so backup/test_connection work without host installs.
# Base: Debian Bookworm. Build context is the repository root.

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Tehran

WORKDIR /app

# PostgreSQL (PGDG client ≥ server), MySQL, Redis CLI, Microsoft ODBC + sqlcmd, unzip/libicu for SqlPackage.
ARG PG_CLIENT_MAJOR=16
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
       ca-certificates \
       gnupg \
       apt-transport-https \
       unzip \
       libicu72 \
       default-mysql-client \
       redis-tools \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
       | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
       > /etc/apt/sources.list.d/pgdg.list \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
       | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list \
       > /etc/apt/sources.list.d/microsoft-prod.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends "postgresql-client-${PG_CLIENT_MAJOR}" \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
       msodbcsql18 \
       mssql-tools18 \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="${PATH}:/opt/mssql-tools18/bin"

# Microsoft SqlPackage (.bacpac export/import for SQL Server).
# Official Linux zip is x64; skip on arm64 so Apple Silicon images still build.
ARG SQLPACKAGE_URL=https://aka.ms/sqlpackage-linux
RUN set -eux \
    && ARCH="$(dpkg --print-architecture)" \
    && case "$ARCH" in \
         amd64) \
           curl -fSL "$SQLPACKAGE_URL" -o /tmp/sp.zip \
           && unzip -q /tmp/sp.zip -d /opt/sqlpackage-root \
           && SP_BIN="$(find /opt/sqlpackage-root -type f -name sqlpackage | head -1)" \
           && test -n "$SP_BIN" \
           && chmod +x "$SP_BIN" \
           && ln -sf "$SP_BIN" /usr/local/bin/sqlpackage \
           && rm /tmp/sp.zip \
           && sqlpackage /version \
           ;; \
         *) echo "SqlPackage Linux zip is x64-only; skipping on $ARCH" ;; \
       esac

# MongoDB Database Tools (mongodump / mongorestore) and mongosh.
# Install from repo.mongodb.org — fastdl.mongodb.org/CloudFront often returns 403
# (missing tarball names, or blocked regions).
ARG MONGO_ORG_MAJOR=8.0
RUN set -eux \
    && ARCH="$(dpkg --print-architecture)" \
    && curl -fsSL "https://pgp.mongodb.com/server-${MONGO_ORG_MAJOR}.asc" \
       | gpg --dearmor -o /usr/share/keyrings/mongodb-server.gpg \
    && case "$ARCH" in \
         amd64) \
           echo "deb [ signed-by=/usr/share/keyrings/mongodb-server.gpg ] http://repo.mongodb.org/apt/debian bookworm/mongodb-org/${MONGO_ORG_MAJOR} main" \
             > /etc/apt/sources.list.d/mongodb-org.list \
           ;; \
         arm64) \
           echo "deb [ arch=arm64 signed-by=/usr/share/keyrings/mongodb-server.gpg ] http://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/${MONGO_ORG_MAJOR} multiverse" \
             > /etc/apt/sources.list.d/mongodb-org.list \
           ;; \
         *) echo "unsupported arch for MongoDB tools: $ARCH"; exit 1 ;; \
       esac \
    && apt-get update \
    && apt-get install -y --no-install-recommends mongodb-database-tools mongodb-mongosh \
    && rm -rf /var/lib/apt/lists/* \
    && mongodump --version \
    && mongosh --version

COPY server/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY server /app

COPY docker/docker-entrypoint.sh /entrypoint.sh
COPY docker/docker-entrypoint.prod.sh /entrypoint.prod.sh
RUN sed -i 's/\r$//' /entrypoint.sh /entrypoint.prod.sh \
    && chmod +x /entrypoint.sh /entrypoint.prod.sh

EXPOSE 8000

# ClickHouse uses HTTP from Python (no clickhouse-client required).
CMD ["gunicorn", "baxconf.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "1800"]

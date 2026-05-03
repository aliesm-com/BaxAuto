# BaxAuto API — DB client binaries so backup/test_connection work without host installs.
# Base: Debian Bookworm.

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# PostgreSQL, MySQL clients, Redis CLI, Microsoft ODBC + sqlcmd, unzip/libicu for SqlPackage.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
       ca-certificates \
       gnupg \
       apt-transport-https \
       unzip \
       libicu72 \
       postgresql-client \
       default-mysql-client \
       redis-tools \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
       | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list \
       > /etc/apt/sources.list.d/microsoft-prod.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
       msodbcsql18 \
       mssql-tools18 \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="${PATH}:/opt/mssql-tools18/bin"

# Microsoft SqlPackage (.bacpac export/import for SQL Server).
ARG SQLPACKAGE_URL=https://aka.ms/sqlpackage-linux-x64
RUN curl -fSL "$SQLPACKAGE_URL" -o /tmp/sp.zip \
    && unzip -q /tmp/sp.zip -d /opt/sqlpackage-root \
    && SP_BIN="$(find /opt/sqlpackage-root -type f -name sqlpackage | head -1)" \
    && test -n "$SP_BIN" \
    && chmod +x "$SP_BIN" \
    && ln -sf "$SP_BIN" /usr/local/bin/sqlpackage \
    && rm /tmp/sp.zip \
    && sqlpackage /version

# MongoDB Database Tools (mongodump / mongorestore).
ARG MONGO_TOOLS_VERSION=100.9.10
RUN set -eux \
    && ARCH="$(dpkg --print-architecture)" \
    && case "$ARCH" in \
         amd64) MARCH=x86_64 ;; \
         arm64) MARCH=aarch64 ;; \
         *) echo "unsupported arch for MongoDB tools: $ARCH"; exit 1 ;; \
       esac \
    && cd /tmp \
    && curl -fsSL "https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian12-${MARCH}-${MONGO_TOOLS_VERSION}.tgz" \
       | tar xz \
    && mv mongodb-database-tools-debian12-*/bin/* /usr/local/bin/ \
    && rm -rf mongodb-database-tools-* \
    && mongodump --version

# mongosh (better MongoDB test_connection than TCP-only).
ARG MONGOSH_VERSION=2.3.9
RUN set -eux \
    && ARCH="$(dpkg --print-architecture)" \
    && case "$ARCH" in \
         amd64) MS_ARCH=x64 ;; \
         arm64) MS_ARCH=arm64 ;; \
         *) echo "unsupported arch for mongosh: $ARCH"; exit 1 ;; \
       esac \
    && cd /tmp \
    && curl -fsSL \
       "https://downloads.mongodb.com/compass/mongosh-${MONGOSH_VERSION}-linux-${MS_ARCH}.tgz" \
       | tar xz \
    && mv "mongosh-${MONGOSH_VERSION}-linux-${MS_ARCH}/bin/mongosh" /usr/local/bin/mongosh \
    && chmod +x /usr/local/bin/mongosh \
    && rm -rf "/tmp/mongosh-${MONGOSH_VERSION}-linux-${MS_ARCH}" \
    && mongosh --version

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Default production command (docker-compose overrides with runserver for dev).
# ClickHouse uses HTTP from Python (no clickhouse-client required). Optional: rabbitmqadmin for RabbitMQ ops.
CMD ["gunicorn", "baxconf.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

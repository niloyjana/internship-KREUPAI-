# Fresh Machine Setup Guide

This guide is the fastest way to run the project on a new laptop or desktop after cloning from GitHub.

Use this document when:

- a teammate clones the repository on a different PC
- the project works on one machine but not on another
- a clean local setup is needed for onboarding

---

## 1. Required software

Install these versions first.

| Tool           | Required Version | Notes                                             |
| -------------- | ---------------- | ------------------------------------------------- |
| Node.js        | 20+              | Required by the monorepo                          |
| pnpm           | 9+               | Prefer the repository version `10.17.1`           |
| Python         | 3.11+            | Required for `ai-runtime`                         |
| Docker         | 24+              | Required for local infrastructure                 |
| Docker Compose | 2.20+            | Use `docker compose`, not legacy `docker-compose` |
| Git            | 2.40+            | For cloning and pulling                           |

Reference: [docs/onboarding/environment-setup.md](environment-setup.md#L19-L27)

---

## 2. Clone the repository

```bash
git clone <repository-url> KreupAI.AISA
cd KreupAI.AISA
```

If you are on Windows, use WSL2 and clone inside the Linux filesystem, not under `/mnt/c`.

Reference: [docs/onboarding/environment-setup.md](environment-setup.md#L161-L201)

---

## 3. Install Node dependencies from the root

This repository is a `pnpm` monorepo. Do not use `npm install` or `yarn`.

```bash
pnpm install --frozen-lockfile
```

If `--frozen-lockfile` fails because `pnpm` is older than the lockfile format, upgrade `pnpm` first and rerun the command.

Repository scripts and package manager version are defined in [package.json](../../package.json#L1-L24).

---

## 4. Create the local environment file

Copy the template from [.env.example](../../.env.example).

```bash
cp .env.example .env.local
```

Then fill in all required values.

### Minimum required values

These are required by the TypeScript services:

- `DATABASE_URL`
- `REDIS_URL`
- `KAFKA_BROKERS`
- `JWT_PRIVATE_KEY`
- `JWT_PUBLIC_KEY`
- `FIELD_ENCRYPTION_KEY`
- `PLATFORM_URL`
- `ENV`
- `TENANT_ISOLATION_MODE`

Validation is defined in [packages/config/src/env.schema.ts](../../packages/config/src/env.schema.ts#L5-L38).

### Generate local keys

```bash
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
openssl rand -hex 32
```

Use:

- the content of `private.pem` as `JWT_PRIVATE_KEY`
- the content of `public.pem` as `JWT_PUBLIC_KEY`
- the generated hex string as `FIELD_ENCRYPTION_KEY`

### Important note for `ai-runtime`

The Python runtime does not automatically load `.env.local` by itself.

Before starting `ai-runtime`, export the variables into the shell:

```bash
set -a
source .env.local
set +a
```

---

## 5. Start local infrastructure

The local containers are defined in [infrastructure/docker/docker-compose.yml](../../infrastructure/docker/docker-compose.yml#L1-L70).

Start them from the repository root:

```bash
docker compose -f infrastructure/docker/docker-compose.yml up -d
```

Check container health:

```bash
docker compose -f infrastructure/docker/docker-compose.yml ps
```

### Expected local ports

| Service         | Port   |
| --------------- | ------ |
| PostgreSQL      | `5433` |
| Redis           | `6379` |
| Kafka           | `9092` |
| Redis Commander | `8081` |
| Kafka UI        | `8085` |

If any of these ports are already used on the machine, startup may fail.

---

## 6. Generate Prisma client and prepare the database

From the repository root:

```bash
pnpm db:generate
pnpm db:migrate
pnpm db:seed
```

Relevant scripts:

- [package.json](../../package.json#L12-L18)
- [database/package.json](../../database/package.json#L1-L24)

If migration fails on a new machine, first confirm:

- Docker is running
- PostgreSQL container is healthy
- `DATABASE_URL` matches the local port `5433`

---

## 7. Set up Python for `ai-runtime`

Create and activate a virtual environment inside [ai-runtime](../../ai-runtime):

```bash
cd ai-runtime
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

### Important correction

Some older onboarding instructions refer to `requirements/dev.txt`. That file does not exist in this repository.

Use [ai-runtime/requirements.txt](../../ai-runtime/requirements.txt) instead.

---

## 8. Start the project

Use two terminals.

### Terminal 1 — start the Node monorepo

From the repository root:

```bash
pnpm dev
```

This runs the monorepo development processes through Turbo.

### Terminal 2 — start the Python runtime

From the repository root:

```bash
set -a
source .env.local
set +a
cd ai-runtime
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The root `dev` script does not start `ai-runtime` automatically.

---

## 9. Quick verification checklist

After startup, verify these basics:

- Docker containers are healthy
- `pnpm install` completed without workspace errors
- Prisma client was generated successfully
- database migration completed successfully
- Python virtual environment is active in the `ai-runtime` terminal
- `uvicorn` started without import or environment errors
- no required environment variable is missing

Recommended checks:

```bash
docker compose -f infrastructure/docker/docker-compose.yml ps
pnpm db:generate
```

If needed, inspect logs:

```bash
docker compose -f infrastructure/docker/docker-compose.yml logs postgres
docker compose -f infrastructure/docker/docker-compose.yml logs redis
docker compose -f infrastructure/docker/docker-compose.yml logs kafka
```

---

## 10. Common reasons the project works on one PC but not another

### Version mismatch

- wrong Node.js version
- old `pnpm` version
- Python below `3.11`

### Environment mismatch

- `.env.local` not created
- invalid `DATABASE_URL`
- missing JWT keys
- missing `FIELD_ENCRYPTION_KEY`

### Infrastructure not running

- Docker Desktop not started
- PostgreSQL or Redis container unhealthy
- port conflicts on `5433`, `6379`, or `9092`

### Python runtime setup incomplete

- virtual environment not created
- dependencies not installed from `ai-runtime/requirements.txt`
- `.env.local` not exported before running `uvicorn`

### Monorepo install issues

- `npm install` used instead of `pnpm install`
- install command run from a subfolder instead of the repository root

---

## 11. Clean restart procedure

If a new machine gets into a bad state, use this reset flow.

### Stop local processes

```bash
docker compose -f infrastructure/docker/docker-compose.yml down
```

### Optional: remove local container data

```bash
docker compose -f infrastructure/docker/docker-compose.yml down -v
```

### Reinstall and restart

```bash
pnpm install --frozen-lockfile
pnpm db:generate
docker compose -f infrastructure/docker/docker-compose.yml up -d
pnpm db:migrate
pnpm db:seed
```

Then restart the Node and Python processes.

---

## 12. Recommended onboarding order for every new PC

1. Install Node, `pnpm`, Python, Docker, and Git
2. Clone the repository
3. Run `pnpm install --frozen-lockfile`
4. Copy `.env.example` to `.env.local`
5. Fill required environment variables
6. Start Docker infrastructure
7. Run Prisma generate, migrate, and seed
8. Create Python virtual environment in `ai-runtime`
9. Install Python dependencies from `ai-runtime/requirements.txt`
10. Start `pnpm dev`
11. Start `uvicorn` for `ai-runtime`

---

## 13. File references

- [docs/onboarding/environment-setup.md](environment-setup.md)
- [.env.example](../../.env.example)
- [package.json](../../package.json)
- [database/package.json](../../database/package.json)
- [infrastructure/docker/docker-compose.yml](../../infrastructure/docker/docker-compose.yml)
- [ai-runtime/requirements.txt](../../ai-runtime/requirements.txt)

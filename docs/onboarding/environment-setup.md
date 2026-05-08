# Environment Setup Guide

This guide covers system requirements, platform-specific setup instructions, environment variable configuration, IDE setup, and troubleshooting for the ADWP development environment.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [macOS Setup Guide](#macos-setup-guide)
3. [Linux Setup Guide](#linux-setup-guide)
4. [Windows (WSL2) Setup Guide](#windows-wsl2-setup-guide)
5. [Environment Variables Reference](#environment-variables-reference)
6. [IDE Setup](#ide-setup)
7. [Troubleshooting Common Setup Issues](#troubleshooting-common-setup-issues)

---

## System Requirements

| Requirement        | Version     | Purpose                                           |
|--------------------|-------------|---------------------------------------------------|
| Node.js            | >= 20.0.0   | TypeScript services and Next.js apps               |
| pnpm               | >= 9.0.0    | Package manager (monorepo workspaces)              |
| Python             | >= 3.11     | AI Runtime (FastAPI, agent logic)                  |
| Docker             | >= 24.0     | Infrastructure services (PostgreSQL, Redis, Kafka) |
| Docker Compose     | >= 2.20     | Multi-container orchestration                      |
| Git                | >= 2.40     | Version control                                    |

**Recommended hardware:**

| Resource   | Minimum         | Recommended       |
|------------|-----------------|-------------------|
| RAM        | 8 GB            | 16 GB             |
| CPU        | 4 cores         | 8 cores           |
| Disk       | 20 GB free      | 50 GB free        |

Docker Desktop requires significant resources. Allocate at least **4 GB RAM** and **2 CPUs** to Docker in its settings.

---

## macOS Setup Guide

### 1. Install Homebrew (if not present)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Node.js 20

```bash
brew install node@20

# Verify
node --version   # v20.x.x
npm --version    # 10.x.x
```

### 3. Install pnpm

```bash
npm install -g pnpm

# Verify
pnpm --version   # 9.x.x or 10.x.x
```

### 4. Install Python 3.11+

```bash
brew install python@3.11

# Verify
python3 --version   # Python 3.11.x or higher
```

### 5. Install Docker Desktop

Download and install from [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/).

After installation:
1. Open Docker Desktop.
2. Go to Settings > Resources.
3. Allocate at least 4 GB memory and 2 CPUs.
4. Apply and restart.

```bash
# Verify
docker --version           # Docker version 24.x.x
docker compose version     # Docker Compose version v2.x.x
```

### 6. Install Additional Tools

```bash
# Git (usually pre-installed on macOS)
brew install git

# Optional but recommended
brew install jq             # JSON processor for API testing
brew install kubectl        # Kubernetes CLI (for staging/production)
brew install awscli         # AWS CLI (for staging/production)
```

### 7. Clone and Setup

```bash
git clone <repository-url> KreupAI.AISA
cd KreupAI.AISA

# Install Node dependencies
pnpm install

# Generate Prisma client
pnpm db:generate

# Start infrastructure
docker compose -f infrastructure/docker/docker-compose.yml up -d

# Run database migrations and seed
pnpm db:migrate
pnpm db:seed

# Setup Python environment
cd ai-runtime
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements/dev.txt
cd ..

# Start everything
pnpm dev                    # In terminal 1
cd ai-runtime && source .venv/bin/activate && uvicorn api.main:app --reload  # In terminal 2
```

---

## Linux Setup Guide

Tested on Ubuntu 22.04 LTS and Debian 12. Adjust package manager commands for other distributions.

### 1. Install Node.js 20

```bash
# Using NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version
npm --version
```

### 2. Install pnpm

```bash
npm install -g pnpm

# Verify
pnpm --version
```

### 3. Install Python 3.11+

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip

# Verify
python3.11 --version
```

### 4. Install Docker and Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com | sudo sh

# Add your user to the docker group (avoids sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### 5. Install Additional Tools

```bash
sudo apt install -y git curl jq
```

### 6. Clone and Setup

```bash
git clone <repository-url> KreupAI.AISA
cd KreupAI.AISA

pnpm install
pnpm db:generate

docker compose -f infrastructure/docker/docker-compose.yml up -d

pnpm db:migrate
pnpm db:seed

cd ai-runtime
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements/dev.txt
cd ..

pnpm dev
```

---

## Windows (WSL2) Setup Guide

ADWP development on Windows requires Windows Subsystem for Linux 2 (WSL2).

### 1. Enable WSL2

```powershell
# Run PowerShell as Administrator
wsl --install

# Restart your computer, then install Ubuntu
wsl --install -d Ubuntu-22.04
```

### 2. Install Docker Desktop for Windows

1. Download from [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/).
2. During installation, ensure "Use WSL 2 based engine" is checked.
3. In Docker Desktop Settings > Resources > WSL Integration:
   - Enable integration with your Ubuntu distribution.
4. Allocate at least 4 GB memory.

### 3. Setup Inside WSL2

Open your WSL2 Ubuntu terminal and follow the [Linux Setup Guide](#linux-setup-guide) above.

**Important WSL2 notes:**

- Clone the repository inside the WSL2 filesystem (`/home/user/`), not on the Windows mount (`/mnt/c/`). The Windows mount is significantly slower for file I/O.
- Use the WSL2 terminal for all commands, not PowerShell.
- Docker commands work seamlessly inside WSL2 when Docker Desktop integration is enabled.

```bash
# Clone in WSL2 home directory (fast filesystem)
cd ~
git clone <repository-url> KreupAI.AISA
cd KreupAI.AISA

# Continue with standard setup...
```

### 4. VS Code Remote - WSL

Install the [WSL extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-wsl) for VS Code:

```bash
# Open VS Code from WSL
code .
```

This opens VS Code on Windows but connected to the WSL2 environment, giving you the best of both worlds.

---

## Environment Variables Reference

The platform uses environment variables for configuration. A `.env.example` file is provided at the repository root. Copy it to `.env` and customize:

```bash
cp .env.example .env
```

### Core Variables

| Variable                  | Default                                        | Description                              |
|---------------------------|------------------------------------------------|------------------------------------------|
| `DATABASE_URL`            | `postgresql://adwp:adwp_dev_password@localhost:5433/adwp_dev` | PostgreSQL connection string |
| `REDIS_URL`               | `redis://:adwp_dev_password@localhost:6379`     | Redis connection string                  |
| `KAFKA_BROKERS`           | `localhost:9092`                                | Kafka broker addresses                   |
| `NODE_ENV`                | `development`                                   | Node environment                         |
| `ENV`                     | `development`                                   | Platform environment                     |
| `LOG_LEVEL`               | `debug`                                         | Logging level                            |

### Authentication

| Variable                  | Default     | Description                              |
|---------------------------|-------------|------------------------------------------|
| `JWT_SECRET`              | (required)  | Secret key for JWT signing               |
| `JWT_ACCESS_EXPIRY`       | `15m`       | Access token expiry duration             |
| `JWT_REFRESH_EXPIRY`      | `7d`        | Refresh token expiry duration            |

### LLM Configuration

| Variable                  | Default     | Description                              |
|---------------------------|-------------|------------------------------------------|
| `OPENAI_API_KEY`          | (optional)  | OpenAI API key. If unset, mock responses used |
| `ANTHROPIC_API_KEY`       | (optional)  | Anthropic API key. If unset, mock responses used |
| `LLM_DEFAULT_PROVIDER`    | `openai`    | Default LLM provider (`openai` or `anthropic`) |

### Service Ports

| Variable                  | Default     | Description                              |
|---------------------------|-------------|------------------------------------------|
| `AUTH_SERVICE_PORT`        | `3010`      | Auth service port                        |
| `TENANT_SERVICE_PORT`     | `3011`      | Tenant service port                      |
| `SUBSCRIPTION_SERVICE_PORT` | `3012`   | Subscription service port                |
| `AGENT_REGISTRY_PORT`     | `3013`      | Agent registry port                      |
| `WORKFLOW_SERVICE_PORT`   | `3014`      | Workflow service port                    |
| `INTEGRATION_HUB_PORT`   | `3015`      | Integration hub port                     |
| `NOTIFICATION_SERVICE_PORT` | `3016`   | Notification service port                |
| `ANALYTICS_SERVICE_PORT`  | `3017`      | Analytics service port                   |
| `AI_RUNTIME_PORT`         | `8000`      | AI runtime (FastAPI) port                |
| `PORTAL_PORT`             | `3000`      | Portal frontend port                     |
| `ADMIN_PORT`              | `3001`      | Admin frontend port                      |

### Third-Party Integrations (Optional for Local Dev)

| Variable                  | Description                              |
|---------------------------|------------------------------------------|
| `STRIPE_SECRET_KEY`       | Stripe API key for billing               |
| `STRIPE_WEBHOOK_SECRET`   | Stripe webhook signing secret            |
| `SENDGRID_API_KEY`        | SendGrid key for email notifications     |
| `TWILIO_ACCOUNT_SID`      | Twilio SID for SMS notifications         |
| `TWILIO_AUTH_TOKEN`       | Twilio auth token                        |
| `SLACK_BOT_TOKEN`         | Slack bot token for Slack notifications  |

### Multi-Tenancy

| Variable                  | Default     | Description                              |
|---------------------------|-------------|------------------------------------------|
| `TENANT_ISOLATION_MODE`   | `rls`       | Tenant isolation strategy                |

---

## IDE Setup

### VS Code (Recommended)

#### Required Extensions

| Extension                        | Purpose                                  |
|----------------------------------|------------------------------------------|
| Prisma                           | Schema highlighting and formatting       |
| ESLint                           | TypeScript/JavaScript linting            |
| Prettier                         | Code formatting                          |
| Python                           | Python language support                  |
| Pylance                          | Python type checking                     |

#### Recommended Extensions

| Extension                        | Purpose                                  |
|----------------------------------|------------------------------------------|
| Thunder Client or REST Client    | API testing from VS Code                 |
| Docker                           | Docker container management              |
| GitLens                          | Enhanced Git integration                 |
| Tailwind CSS IntelliSense        | Tailwind class autocomplete              |
| Error Lens                       | Inline error display                     |
| YAML                             | YAML file support                        |
| DotENV                           | .env file syntax highlighting            |

#### VS Code Settings

Add to your workspace `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit"
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.python",
    "editor.formatOnSave": true
  },
  "[prisma]": {
    "editor.defaultFormatter": "Prisma.prisma"
  },
  "python.defaultInterpreterPath": "${workspaceFolder}/ai-runtime/.venv/bin/python",
  "python.analysis.typeCheckingMode": "basic",
  "typescript.tsdk": "node_modules/typescript/lib",
  "files.exclude": {
    "**/node_modules": true,
    "**/.turbo": true,
    "**/__pycache__": true,
    "**/.pytest_cache": true
  }
}
```

### JetBrains (WebStorm / PyCharm)

- Open the project root as a single project.
- Configure Node.js interpreter to version 20+.
- Configure Python interpreter to the virtual environment at `ai-runtime/.venv/bin/python`.
- Install the Prisma plugin from the JetBrains marketplace.
- Enable ESLint integration in Settings > Languages & Frameworks > JavaScript > Code Quality Tools > ESLint.

---

## Troubleshooting Common Setup Issues

### Docker: Port Already in Use

```
Error: Bind for 0.0.0.0:5433 failed: port is already allocated
```

**Fix:** Another process is using the port. Find and stop it:

```bash
# Find what's using the port
lsof -i :5433

# Kill the process (use the PID from above)
kill -9 <PID>

# Or change the port in docker-compose.yml
```

### Docker: Containers Not Starting

```bash
# Check container logs
docker compose -f infrastructure/docker/docker-compose.yml logs

# Restart from scratch
docker compose -f infrastructure/docker/docker-compose.yml down -v
docker compose -f infrastructure/docker/docker-compose.yml up -d
```

### Prisma: Migration Failed

```
Error: P3009: migrate found failed migrations in the target database
```

**Fix:**

```bash
# Reset the database (WARNING: destroys all data)
DATABASE_URL="postgresql://adwp:adwp_dev_password@localhost:5433/adwp_dev" npx prisma migrate reset

# Re-run migrations and seed
pnpm db:migrate
pnpm db:seed
```

### Prisma: Schema Out of Sync

```
Error: The database schema is not empty
```

**Fix:**

```bash
# Pull current database state
npx prisma db pull

# Re-generate client
pnpm db:generate
```

### pnpm Install: Peer Dependency Errors

```
ERR_PNPM_PEER_DEP_ISSUES
```

**Fix:** These warnings are usually non-blocking. If a package truly fails to install:

```bash
# Clear pnpm cache and retry
pnpm store prune
rm -rf node_modules
pnpm install
```

### Python: Module Not Found

```
ModuleNotFoundError: No module named 'agents'
```

**Fix:** The AI Runtime uses relative imports that require running from the `ai-runtime/` directory:

```bash
cd ai-runtime
source .venv/bin/activate
uvicorn api.main:app --reload
```

Or set `PYTHONPATH`:

```bash
export PYTHONPATH=/path/to/KreupAI.AISA/ai-runtime:$PYTHONPATH
```

### Kafka: Connection Refused

```
KafkaError: Connection refused: localhost:9092
```

**Fix:** Kafka takes longer to start than other services. Wait and retry:

```bash
# Check if Kafka is ready
docker compose -f infrastructure/docker/docker-compose.yml logs kafka | tail -20

# If still starting, wait a moment and check again
docker compose -f infrastructure/docker/docker-compose.yml ps
```

### Node.js: Wrong Version

```
error @adwp/root@1.0.0: The engine "node" is incompatible with this module.
```

**Fix:** Ensure you have Node.js 20+:

```bash
node --version

# If using nvm:
nvm install 20
nvm use 20
```

### Redis: Authentication Failed

```
NOAUTH Authentication required
```

**Fix:** The local Redis instance requires a password. Ensure your `REDIS_URL` includes it:

```
redis://:adwp_dev_password@localhost:6379
```

### Docker: Insufficient Disk Space

```
No space left on device
```

**Fix:**

```bash
# Remove unused Docker resources
docker system prune -a

# Check Docker disk usage
docker system df
```

### macOS: Apple Silicon (M1/M2/M3) Issues

If Docker images fail to build or run on Apple Silicon:

```bash
# Force platform in docker-compose.yml if needed
# Add to a service definition:
# platform: linux/amd64

# Or use Rosetta emulation in Docker Desktop settings
```

Verify Docker Desktop has Rosetta emulation enabled:
- Docker Desktop > Settings > General > "Use Rosetta for x86_64/amd64 emulation on Apple Silicon"

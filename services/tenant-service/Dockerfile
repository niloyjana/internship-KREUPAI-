# ---- Builder Stage ----
FROM node:20-alpine AS builder
WORKDIR /app

# Copy workspace root files
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./

# Copy shared packages and database
COPY packages/ ./packages/
COPY database/ ./database/

# Copy the service
COPY services/tenant-service/ ./services/tenant-service/

# Install dependencies and build
RUN corepack enable pnpm && pnpm install --frozen-lockfile
RUN pnpm turbo build --filter=@adwp/tenant-service

# ---- Runner Stage ----
FROM node:20-alpine AS runner
WORKDIR /app

RUN addgroup -g 1001 -S nodejs && adduser -S nestjs -u 1001

COPY --from=builder --chown=nestjs:nodejs /app/services/tenant-service/dist ./dist
COPY --from=builder --chown=nestjs:nodejs /app/node_modules ./node_modules

USER nestjs

EXPOSE 3011

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3011/health || exit 1

CMD ["node", "dist/main.js"]

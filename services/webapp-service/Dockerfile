# Production Dockerfile for Next.js webapp-service
# Multi-stage build optimized for minimal image size

# ============================================
# Stage 1: Dependencies
# ============================================
FROM node:20-alpine AS deps

WORKDIR /app

# Install libc6-compat for Alpine compatibility
RUN apk add --no-cache libc6-compat

# Enable pnpm via corepack with specific version for consistency
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

# Copy package files
COPY package.json pnpm-lock.yaml* ./

# Install dependencies (use --no-frozen-lockfile if lockfile might be stale)
RUN pnpm install --frozen-lockfile || pnpm install

# ============================================
# Stage 2: Builder
# ============================================
FROM node:20-alpine AS builder

WORKDIR /app

# Enable pnpm with same version
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

# Build arguments for NEXT_PUBLIC_* variables (required at build time)
ARG NEXT_PUBLIC_AUTH_SERVICE_URL=https://api.finio.cloud/api/v1/auth
ARG NEXT_PUBLIC_SEARCH_SERVICE_URL=https://api.finio.cloud/api/v1
ARG NEXT_PUBLIC_USER_SERVICE_URL=https://api.finio.cloud/api/v1/users
ARG NEXT_PUBLIC_WATCHLIST_SERVICE_URL=https://api.finio.cloud/api/v1/watchlist
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY

# Set as environment variables for the build
ENV NEXT_PUBLIC_AUTH_SERVICE_URL=$NEXT_PUBLIC_AUTH_SERVICE_URL
ENV NEXT_PUBLIC_SEARCH_SERVICE_URL=$NEXT_PUBLIC_SEARCH_SERVICE_URL
ENV NEXT_PUBLIC_USER_SERVICE_URL=$NEXT_PUBLIC_USER_SERVICE_URL
ENV NEXT_PUBLIC_WATCHLIST_SERVICE_URL=$NEXT_PUBLIC_WATCHLIST_SERVICE_URL
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy all source code
COPY . .

# Set build-time environment variables
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Build the application
RUN pnpm build

# ============================================
# Stage 3: Runner (Production)
# ============================================
FROM node:20-alpine AS runner

WORKDIR /app

# Set production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built assets from builder
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Start the server
CMD ["node", "server.js"]

# Multi-stage build cho Next.js
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install pnpm globally và install dependencies
RUN npm install -g pnpm && pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build Next.js app
RUN pnpm run build


# Production stage
FROM node:20-alpine

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files từ builder
COPY package.json pnpm-lock.yaml ./

# Install dependencies - production only
RUN pnpm install --prod --frozen-lockfile

# Copy built app từ builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# Environment variables
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000', (r) => {if (r.statusCode !== 200) throw new Error(r.statusCode)})"

# Expose port
EXPOSE 3000

# Run Next.js
CMD ["pnpm", "start"]

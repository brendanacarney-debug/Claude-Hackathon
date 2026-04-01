FROM node:22-slim AS deps

WORKDIR /app/web-app
COPY web-app/package.json web-app/package-lock.json ./
RUN npm ci

FROM node:22-slim AS builder

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app
COPY --from=deps /app/web-app/node_modules ./web-app/node_modules
COPY web-app ./web-app
COPY fixtures ./fixtures

WORKDIR /app/web-app
RUN npm run build

FROM node:22-slim AS runner

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

WORKDIR /app

COPY --from=builder /app/web-app/.next/standalone ./
COPY --from=builder /app/web-app/.next/static ./web-app/.next/static
COPY --from=builder /app/web-app/public ./web-app/public
COPY --from=builder /app/fixtures ./fixtures

EXPOSE 3000

CMD ["node", "server.js"]

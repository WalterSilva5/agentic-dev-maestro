#!/bin/sh
set -e

echo "[entrypoint] Applying database migrations..."
npx prisma migrate deploy

echo "[entrypoint] Seeding database (skipped if already seeded)..."
npx prisma db seed || echo "[entrypoint] Seed skipped or failed (non-fatal)."

echo "[entrypoint] Starting API..."
exec node dist/main

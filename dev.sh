#!/usr/bin/env bash
set -e

# Frontend
(
  cd web
  npm run dev
) &

# Backend
(
  cd backend
  ./run.sh
) &

wait

# Infrastructure / SRE Intern Assignment

**Full Name:** Sulav Singhal

**Date:** 2026-04-30

**GitHub Repository:** https://github.com/SulavSinghal/ZEOTAP.git

## Implementation Summary

This submission implements an Incident Management System (IMS) consisting of:

- FastAPI ingestion service with `POST /ingest` (queues to Redis)
- Background async worker that reads Redis `signal_queue`, writes raw signals to MongoDB, and creates incidents in Postgres with debouncing logic
- MongoDB used as a data lake for raw signals
- Redis used as message broker and lightweight lock (SETNX) for debouncing
- PostgreSQL as the source-of-truth for incidents
- Frontend dashboard (Vite + React) that polls `GET /incidents`
- Docker Compose for local development with named volumes and healthchecks

## How I validated

- Built frontend (`npm run build`) — success
- Started infrastructure with `docker-compose up -d` and verified containers running
- Installed backend dependencies and ran FastAPI and worker locally
- Ran integration test: posted a test signal and polled `/incidents` until an incident appeared

## Non-Functional Notes

- Security: Uses `.env` for development; recommend secrets manager for production and tighten CORS.
- Performance: Ingestion is O(1) enqueue; worker can be horizontally scaled; consider batching DB writes.
- Observability: Basic metrics logger included; recommend Prometheus/Grafana for production.
- Scalability & Reliability: Designed to scale workers; use orchestration (K8s) and backups for DBs.

## How to run locally

See the repository README for full instructions. Minimal steps:

```powershell
cd <repo-root>
docker-compose up -d
cd backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 3000
python worker.py
cd frontend/ims-frontend
npm run dev
```

## Checklist

- [x] Ingestion API implemented
- [x] Worker implemented and tested locally
- [x] Mongo/Redis/Postgres wired and running via Docker Compose
- [x] Frontend wired and builds successfully
- [x] Integration test included

## Contact

If anything fails during run, contact: Sulav Singhal sulavsinghal01@gmail.com

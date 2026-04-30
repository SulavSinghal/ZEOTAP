import asyncio
import json
import time
from fastapi import FastAPI, Request, HTTPException, status
from redis.asyncio import Redis, ConnectionPool

app = FastAPI(title="Mission-Critical IMS Engine")

# Connect to the Redis container running via Docker Compose
redis_pool = ConnectionPool.from_url("redis://localhost:6379", decode_responses=True)
redis_client = Redis(connection_pool=redis_pool)

# --- Observability Metrics ---
metrics_state = {
    "signals_ingested": 0
}

async def log_metrics():
    """Background task to print throughput every 5 seconds[cite: 2]."""
    while True:
        await asyncio.sleep(5)
        throughput = metrics_state["signals_ingested"] / 5
        print(f"[Metrics] Throughput: {throughput} signals/sec")
        metrics_state["signals_ingested"] = 0

@app.on_event("startup")
async def startup_event():
    # Start the metrics logger in the background when the server boots
    asyncio.create_task(log_metrics())

# --- Endpoints ---

@app.get("/health")
async def health_check():
    """
    Advanced SRE Health Check.
    Verifies the connection to critical dependencies (Redis)[cite: 2].
    """
    system_health = {"status": "healthy", "time": time.time(), "redis": "unknown"}
    try:
        await redis_client.ping()
        system_health["redis"] = "up"
    except Exception:
        system_health["status"] = "unhealthy"
        system_health["redis"] = "down"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=system_health
        )
    return system_health

@app.post("/ingest", status_code=202)
async def ingest_signal(request: Request):
    """
    High-throughput ingestion endpoint.
    Accepts the payload and instantly pushes it to Redis (O(1) time complexity)[cite: 2].
    """
    signal_data = await request.json()
    signal_data['ingested_at'] = time.time()
    
    # Push to Redis list 'signal_queue' immediately
    await redis_client.lpush("signal_queue", json.dumps(signal_data))
    
    metrics_state["signals_ingested"] += 1
    
    # Return 202 Accepted immediately - DO NOT wait for a database write!
    return {"status": "queued"}
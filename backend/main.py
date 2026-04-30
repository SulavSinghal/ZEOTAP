import asyncio
import json
import time
from fastapi import FastAPI, Request, HTTPException, status
from redis.asyncio import Redis, ConnectionPool
from motor.motor_asyncio import AsyncIOMotorClient
import psycopg
from psycopg.rows import dict_row
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
app = FastAPI(title="Mission-Critical IMS Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, you'd specify the frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)


mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
mongo_db = mongo_client["ims_lake"]

PG_URL = "postgresql://admin:secretpassword@localhost:5433/ims_db"


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

@app.get("/incidents")
async def get_incidents():
    """Fetch all incidents for the Dashboard[cite: 2]."""
    async with await psycopg.AsyncConnection.connect(PG_URL, row_factory=dict_row) as aconn:
        async with aconn.cursor() as acur:
            await acur.execute("SELECT * FROM incidents ORDER BY start_time DESC")
            return await acur.fetchall()

@app.get("/incidents/{component_id}/signals")
async def get_raw_signals(component_id: str):
    """Fetch raw signals from MongoDB for the detail view[cite: 2]."""
    cursor = mongo_db["raw_signals"].find({"component_id": component_id}).limit(100)
    return await cursor.to_list(length=100)
# --- RCA Schema ---
class RcaUpdate(BaseModel):
    root_cause: str
    fix_applied: str
    prevention_steps: str

@app.patch("/incidents/{incident_id}/close")
async def close_incident(incident_id: int, rca: RcaUpdate):
    """
    Mandatory RCA: Rejects closing if data is missing.
    Calculates MTTR automatically.
    """
    if not rca.root_cause or not rca.fix_applied:
        raise HTTPException(status_code=400, detail="RCA details are mandatory to close an incident.")

    async with await psycopg.AsyncConnection.connect(PG_URL, row_factory=dict_row) as aconn:
        async with aconn.cursor() as acur:
            # Check if incident exists
            await acur.execute("SELECT start_time FROM incidents WHERE id = %s", (incident_id,))
            row = await acur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Incident not found")

            end_time = datetime.now()
            # Calculate MTTR in minutes
            start_time = row['start_time']
            mttr_minutes = (end_time - start_time.replace(tzinfo=None)).total_seconds() / 60

            # Use .dict() for Pydantic v1, or .model_dump() for Pydantic v2
            rca_dict = rca.model_dump() if hasattr(rca, 'model_dump') else rca.dict()

            await acur.execute(
                """
                UPDATE incidents 
                SET status = 'CLOSED', rca_data = %s, end_time = %s
                WHERE id = %s
                """,
                (json.dumps(rca_dict), end_time, incident_id)
            )
        await aconn.commit()
        return {"status": "CLOSED", "mttr_minutes": round(mttr_minutes, 2)}
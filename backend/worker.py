import asyncio
import json
from redis.asyncio import Redis
from motor.motor_asyncio import AsyncIOMotorClient
import psycopg

# --- Database Connections ---
redis_client = Redis.from_url("redis://localhost:6379", decode_responses=True)

# MongoDB (Data Lake for raw signals)
mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
mongo_db = mongo_client["ims_lake"]
mongo_collection = mongo_db["raw_signals"]

# PostgreSQL connection string
PG_URL = "postgresql://admin:secretpassword@localhost:5433/ims_db"

async def setup_postgres():
    """Ensure the Postgres table exists before we start inserting data."""
    async with await psycopg.AsyncConnection.connect(PG_URL) as aconn:
        async with aconn.cursor() as acur:
            await acur.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id SERIAL PRIMARY KEY,
                    component_id VARCHAR(255) NOT NULL,
                    status VARCHAR(50) DEFAULT 'OPEN',
                    rca_data TEXT,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP
                );
            """)
        await aconn.commit()

async def process_queue():
    print("🚀 Worker started. Listening to Redis 'signal_queue'...")
    await setup_postgres()
    
    # Keep a persistent connection open to Postgres
    async with await psycopg.AsyncConnection.connect(PG_URL) as aconn:
        while True:
            # 1. Pull from the Queue (blocks for 1 second if empty to save CPU)
            result = await redis_client.brpop("signal_queue", timeout=1)
            if not result:
                continue
                
            _, item = result
            signal = json.loads(item)
            
            # The system expects a 'component_id' in the JSON (e.g., "CACHE_CLUSTER_01")
            component_id = signal.get("component_id", "UNKNOWN_COMPONENT")
            
            # 2. Data Lake: Save the raw payload to MongoDB immediately
            await mongo_collection.insert_one(signal)
            
            # 3. Debouncing Logic: Use Redis SETNX to lock this component for 10 seconds
            lock_key = f"incident_lock:{component_id}"
            is_new_incident = await redis_client.set(lock_key, "active", nx=True, ex=10)
            
            if is_new_incident:
                # 4. Source of Truth: If lock is acquired, it's a NEW incident!
                print(f"🚨 [ALERT] New failure on {component_id}! Creating Postgres Ticket.")
                async with aconn.cursor() as acur:
                    await acur.execute(
                        "INSERT INTO incidents (component_id, status) VALUES (%s, %s)",
                        (component_id, 'OPEN')
                    )
                await aconn.commit()
            else:
                # If we get here, the signal was saved to Mongo, but ignored by Postgres 
                # because an incident ticket was already opened in the last 10 seconds.
                print(f"    ↳ [DEBOUNCED] {component_id} already failing. Saved to Mongo only.")

if __name__ == "__main__":
    # Run the async worker loop
    # On Windows, psycopg requires SelectorEventLoop instead of ProactorEventLoop
    asyncio.run(process_queue(), loop_factory=asyncio.SelectorEventLoop)
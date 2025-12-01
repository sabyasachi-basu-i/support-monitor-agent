from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime,timezone
import asyncio

MONGO_URI = "mongodb://10.0.0.239:27017"
DATABASE_NAME = "automation_logs_db"

client = AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]

# Required collections
REQUIRED_COLLECTIONS = ["jobs", "executions", "logs", "rca", "auditlogs"]

async def ensure_collections():
    existing_collections = await db.list_collection_names()
    for col in REQUIRED_COLLECTIONS:
        if col not in existing_collections:
            print(f"⚡ Collection '{col}' not found, creating it...")
            await db.create_collection(col)
        else:
            print(f"✔ Collection '{col}' already exists.")


async def watch_jobs_changes():
    while True:
        try:
            collection = db.jobs
            audit_collection = db.auditlogs
            async with collection.watch() as change_stream:
                async for change in change_stream:
                    log_entry = {
                        "timestamp": datetime.now(timezone.utc),
                        "operation_type": change.get("operationType"),
                        "document_key": change.get("documentKey"),
                        "full_document": change.get("fullDocument"),
                        "update_description": change.get("updateDescription"),
                    }
                    await audit_collection.insert_one(log_entry)
                    print("✅ Logged change:", log_entry)
        except Exception as e:
            print("⚠ Error in watch_jobs_changes:", e)
            await asyncio.sleep(5)  # Retry after 5 seconds
            
            
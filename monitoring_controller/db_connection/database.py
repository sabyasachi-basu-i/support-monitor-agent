from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb://localhost:27017"
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

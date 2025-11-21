"""
FastAPI Event Receiver - Save this as: api_server.py
Run with: uvicorn api_server:app --host 0.0.0.0 --port 5000 --reload
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import logging
import json
from datetime import datetime
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("event_api")

app = FastAPI(
    title="Event Receiver API",
    description="API to receive merged execution events",
    version="1.0.0"
)

# Directory to store received events
EVENTS_DIR = "received_events"
os.makedirs(EVENTS_DIR, exist_ok=True)


# Data model for incoming events
class EventPayload(BaseModel):
    executionid: str
    execution: Dict[str, Any]
    logs: List[Dict[str, Any]]
    log_count: int
    merged_at: float


@app.post("/post_event")
async def post_event(payload: EventPayload):
    """
    Main endpoint to receive fault events from monitoring script
    """
    try:
        executionid = payload.executionid
        
        # Log received event details
        logger.info("=" * 70)
        logger.info(f"📥 RECEIVED EVENT: {executionid}")
        logger.info(f"   State: {payload.execution.get('state', 'unknown')}")
        logger.info(f"   Process: {payload.execution.get('processname', 'unknown')}")
        logger.info(f"   Log Count: {payload.log_count}")
        logger.info("=" * 70)
        
        # Print full payload for debugging
        print("\n🔍 FULL PAYLOAD:")
        print(json.dumps(payload.dict(), indent=2, default=str))
        print()
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{EVENTS_DIR}/event_{executionid}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(payload.dict(), f, indent=2, default=str)
        
        logger.info(f"💾 Saved to: {filename}")
        
        # Your custom processing here
        await process_event(payload)
        
        return {
            "status": "success",
            "message": f"Event received successfully",
            "executionid": executionid,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


async def process_event(payload: EventPayload):
    """
    Add your custom logic here
    """
    # Example: Count error logs
    error_logs = [
        log for log in payload.logs 
        if 'error' in str(log.get('message', '')).lower()
    ]
    
    if error_logs:
        logger.warning(f"   ⚠️  Found {len(error_logs)} error messages")
    
    # Add your custom processing:
    # - Send email alerts
    # - Store in database
    # - Trigger other workflows
    # etc.


@app.get("/health")
async def health_check():
    """Check if API is running"""
    return {
        "status": "healthy",
        "service": "Event Receiver API",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/events")
async def list_events():
    """List all received events"""
    try:
        files = sorted(os.listdir(EVENTS_DIR))
        events = []
        
        for filename in files:
            if filename.endswith('.json'):
                filepath = os.path.join(EVENTS_DIR, filename)
                with open(filepath, 'r') as f:
                    event_data = json.load(f)
                    events.append({
                        "filename": filename,
                        "executionid": event_data.get('executionid'),
                        "state": event_data.get('execution', {}).get('state'),
                        "log_count": event_data.get('log_count', 0)
                    })
        
        return {
            "status": "success",
            "count": len(events),
            "events": events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events/{executionid}")
async def get_event(executionid: str):
    """Get specific event details"""
    try:
        matching_files = [
            f for f in os.listdir(EVENTS_DIR)
            if f.startswith(f"event_{executionid}_") and f.endswith('.json')
        ]
        
        if not matching_files:
            raise HTTPException(
                status_code=404,
                detail=f"No event found for {executionid}"
            )
        
        latest_file = sorted(matching_files)[-1]
        filepath = os.path.join(EVENTS_DIR, latest_file)
        
        with open(filepath, 'r') as f:
            event_data = json.load(f)
        
        return {"status": "success", "data": event_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 70)
    logger.info("🚀 EVENT RECEIVER API STARTED")
    logger.info("=" * 70)
    logger.info("Endpoints:")
    logger.info("  POST   http://localhost:5000/post_event")
    logger.info("  GET    http://localhost:5000/health")
    logger.info("  GET    http://localhost:5000/events")
    logger.info("  GET    http://localhost:5000/docs  (Interactive API Docs)")
    logger.info("=" * 70)
    logger.info("Waiting for events...")
    logger.info("")
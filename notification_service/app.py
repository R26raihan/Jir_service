from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from notification.utils import init_firebase, send_to_token, send_multicast, send_to_topic
from notification.schemas.notification import RegisterTokenReq, PushReq

# Load environment variables
load_dotenv()

# Initialize Firebase
init_firebase(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/Users/raihansetiawan/backend_JIR/notification/services/jir-smart-city-firebase-adminsdk-fbsvc-e80f151101.json"))

app = FastAPI(title="JIR Smart City Notification Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for demo (replace with database in production)
device_tokens = []

def admin_auth(x_api_key: str = Header(...)):
    if x_api_key != "admin123":  # Simple hardcoded key for demo
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

@app.get("/")
async def health_check():
    return {"service": "notification", "status": "ok"}

@app.get("/health")
async def health_check_alt():
    return {"service": "notification", "status": "ok"}

@app.post("/api/notification/device/register")
def register_device(payload: RegisterTokenReq):
    """Register device token for push notifications"""
    token = payload.fcm_token
    if token not in device_tokens:
        device_tokens.append({
            "fcm_token": token,
            "platform": payload.platform,
            "registered_at": "2025-01-01T00:00:00Z"  # Demo timestamp
        })
    return {"ok": True, "message": "Device registered successfully"}

@app.post("/api/notification/admin/push", dependencies=[Depends(admin_auth)])
def admin_push(req: PushReq):
    """Send push notification to registered devices"""
    tokens_to_send = []

    if req.tokens:
        tokens_to_send = req.tokens
    elif req.topic:
        try:
            msg_id = send_to_topic(req.topic, req.title, req.body, req.data)
            return {"message_id": msg_id, "success": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send to topic: {str(e)}")
    else:
        # Send to all registered devices
        tokens_to_send = [device["fcm_token"] for device in device_tokens]

    if not tokens_to_send:
        raise HTTPException(status_code=400, detail="No device tokens available")

    try:
        resp = send_multicast(tokens_to_send, req.title, req.body, req.data)
        
        # Normalize response
        normalized = []
        if hasattr(resp, "responses") and isinstance(resp.responses, list):
            for idx, r in enumerate(resp.responses):
                if getattr(r, "success", False):
                    normalized.append({
                        "token": tokens_to_send[idx] if idx < len(tokens_to_send) else None,
                        "success": True,
                        "message_id": getattr(r, "message_id", None)
                    })
                else:
                    err = getattr(r, "error", None) or str(getattr(r, "exception", "Unknown error"))
                    normalized.append({
                        "token": tokens_to_send[idx] if idx < len(tokens_to_send) else None,
                        "success": False,
                        "error": err
                    })
        else:
            # Fallback response format
            for i, token in enumerate(tokens_to_send):
                normalized.append({
                    "token": token,
                    "success": True,
                    "message_id": f"msg_{i}"
                })

        return {
            "success_count": getattr(resp, "success_count", len(tokens_to_send)),
            "failure_count": getattr(resp, "failure_count", 0),
            "total_tokens": len(tokens_to_send),
            "details": normalized
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send notifications: {str(e)}")

@app.get("/api/notification/devices")
async def get_registered_devices():
    """Get list of registered devices"""
    return {
        "total_devices": len(device_tokens),
        "devices": device_tokens
    }

@app.post("/api/notification/test")
async def test_notification():
    """Test notification endpoint"""
    try:
        # Send test notification to all devices
        resp = send_multicast(
            [device["fcm_token"] for device in device_tokens],
            "🧪 Test Notification",
            "This is a test notification from JIR Smart City",
            {"test": True, "timestamp": "2025-01-01T00:00:00Z"}
        )
        
        return {
            "success": True,
            "message": "Test notification sent",
            "success_count": getattr(resp, "success_count", 0),
            "failure_count": getattr(resp, "failure_count", 0)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)

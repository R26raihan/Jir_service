from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime

app = FastAPI(title="JIR Smart City Notification Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for demo
device_tokens = []
notification_log = []

class RegisterTokenReq(BaseModel):
    fcm_token: str
    platform: Optional[str] = None

class PushReq(BaseModel):
    title: str
    body: str
    tokens: Optional[List[str]] = None
    topic: Optional[str] = None
    data: Optional[dict] = None

def admin_auth(x_api_key: str = Header(...)):
    if x_api_key != "admin123":
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
    device_info = {
        "fcm_token": token,
        "platform": payload.platform,
        "registered_at": datetime.now().isoformat()
    }
    
    # Check if token already exists
    existing = next((d for d in device_tokens if d["fcm_token"] == token), None)
    if not existing:
        device_tokens.append(device_info)
        print(f"[REGISTER] New device registered: {token[:10]}...")
    else:
        print(f"[REGISTER] Device already exists: {token[:10]}...")
    
    return {"ok": True, "message": "Device registered successfully"}

@app.post("/api/notification/admin/push", dependencies=[Depends(admin_auth)])
def admin_push(req: PushReq):
    """Send push notification to registered devices"""
    tokens_to_send = []

    if req.tokens:
        tokens_to_send = req.tokens
    elif req.topic:
        # Topic-based notification (demo)
        return {
            "message_id": f"topic_{req.topic}_{datetime.now().timestamp()}",
            "success": True,
            "topic": req.topic,
            "message": "Topic notification sent (demo mode)"
        }
    else:
        # Send to all registered devices
        tokens_to_send = [device["fcm_token"] for device in device_tokens]

    if not tokens_to_send:
        raise HTTPException(status_code=400, detail="No device tokens available")

    # Simulate notification sending
    success_count = 0
    failure_count = 0
    details = []
    
    for token in tokens_to_send:
        try:
            # Simulate success/failure (90% success rate)
            import random
            if random.random() < 0.9:
                success_count += 1
                details.append({
                    "token": token[:10] + "...",
                    "success": True,
                    "message_id": f"msg_{datetime.now().timestamp()}"
                })
            else:
                failure_count += 1
                details.append({
                    "token": token[:10] + "...",
                    "success": False,
                    "error": "Simulated failure"
                })
        except Exception as e:
            failure_count += 1
            details.append({
                "token": token[:10] + "...",
                "success": False,
                "error": str(e)
            })

    # Log notification
    notification_log.append({
        "timestamp": datetime.now().isoformat(),
        "title": req.title,
        "body": req.body,
        "success_count": success_count,
        "failure_count": failure_count,
        "data": req.data
    })

    print(f"[NOTIFICATION] Sent: '{req.title}' to {success_count} devices")
    
    return {
        "success_count": success_count,
        "failure_count": failure_count,
        "total_tokens": len(tokens_to_send),
        "details": details
    }

@app.get("/api/notification/devices")
async def get_registered_devices():
    """Get list of registered devices"""
    return {
        "total_devices": len(device_tokens),
        "devices": device_tokens
    }

@app.get("/api/notification/log")
async def get_notification_log():
    """Get notification history"""
    return {
        "total_notifications": len(notification_log),
        "notifications": notification_log[-10:]  # Last 10 notifications
    }

@app.post("/api/notification/test")
async def test_notification():
    """Test notification endpoint"""
    try:
        # Send test notification to all devices
        test_req = PushReq(
            title="🧪 Test Notification",
            body="This is a test notification from JIR Smart City",
            data={"test": True, "timestamp": datetime.now().isoformat()}
        )
        
        result = admin_push(test_req)
        
        return {
            "success": True,
            "message": "Test notification sent",
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)

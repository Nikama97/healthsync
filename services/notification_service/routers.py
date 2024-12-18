# notification_service/routers.py
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from models import Notification
from database import notification_collection
from email_sender import send_email

router = APIRouter()

@router.post("/notifications/send")
async def send_notification(notification: Notification):
    # Save notification to database
    notification_dict = notification.dict()
    notification_collection.insert_one(notification_dict)
    
    # Send email
    success = await send_email(
        notification.recipient_email,
        notification.subject,
        notification.content
    )
    
    if success:
        notification_collection.update_one(
            {"id": notification.id},
            {
                "$set": {
                    "status": "sent",
                    "sent_at": datetime.now()
                }
            }
        )
        return {"message": "Notification sent successfully"}
    else:
        notification_collection.update_one(
            {"id": notification.id},
            {"$set": {"status": "failed"}}
        )
        raise HTTPException(status_code=500, detail="Failed to send notification")

@router.get("/notifications/pending")
async def get_pending_notifications():
    notifications = notification_collection.find({"status": "pending"})
    return [Notification(**notif) for notif in notifications]
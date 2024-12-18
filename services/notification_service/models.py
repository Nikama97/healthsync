# notification_service/models.py
from pydantic import BaseModel
from datetime import datetime
import uuid

class Notification(BaseModel):
    id: str = str(uuid.uuid4())
    recipient_email: str
    subject: str
    content: str
    status: str  # "pending", "sent", "failed"
    created_at: datetime = datetime.now()
    sent_at: datetime = None
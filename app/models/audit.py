from pydantic import BaseModel
from typing import Optional
from enum import Enum


class NotificationStatus(str, Enum):
    """Notification processing status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    DLQ = "dlq"


class AuditLog(BaseModel):
    """Audit log entry for notification"""
    trace_id: str
    user_id: str
    notification_type: str = "push"
    chat_id: str
    sender_name: str
    status: NotificationStatus
    error_message: Optional[str] = None
    metadata: dict = {}
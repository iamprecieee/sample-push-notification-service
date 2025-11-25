from pydantic import BaseModel, Field
from enum import Enum


class NotificationMessage(BaseModel):
    """Message format for push notifications"""

    notification_id: str
    idempotency_key: str
    user_id: str
    chat_id: str
    sender_id: str
    sender_name: str
    message_preview: str
    device_token: str
    priority: int = 1
    metadata: dict = Field(default_factory=dict)
    created_by: str
    timestamp: str


class DlqMessage(BaseModel):
    """Message format for Dead Letter Queue"""

    original_message: NotificationMessage
    failure_reason: str
    failed_at: str


class IdempotencyStatus(str, Enum):
    """Status of idempotency check"""

    NOT_FOUND = "not_found"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"

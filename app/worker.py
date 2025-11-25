import logging
import json
from datetime import datetime, timezone
from app.models import (
    NotificationMessage,
    DlqMessage,
    IdempotencyStatus,
    AuditLog,
    NotificationStatus,
)
from app.clients import RedisClient, DatabaseClient, FcmClient, RabbitMqClient

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Processes push notification messages"""

    def __init__(
        self,
        redis_client: RedisClient,
        database_client: DatabaseClient,
        fcm_client: FcmClient,
        rabbitmq_client: RabbitMqClient,
    ):
        self.redis = redis_client
        self.db = database_client
        self.fcm = fcm_client
        self.rabbitmq = rabbitmq_client

    async def process_message(self, payload: str):
        """Process a single notification message"""
        try:
            message_data = json.loads(payload)
            message = NotificationMessage(**message_data)

            logger.info(
                f"Processing notification: {message.notification_id} "
                f"for user {message.user_id}"
            )

            status = await self.redis.check_idempotency(message.idempotency_key)

            if status == IdempotencyStatus.SENT:
                logger.info(f"Message {message.idempotency_key} already sent, skipping")
                return

            if status == IdempotencyStatus.PROCESSING:
                logger.info(
                    f"Message {message.idempotency_key} is being processed elsewhere"
                )
                return

            await self.redis.mark_as_processing(message.idempotency_key)

            if not message.device_token or len(message.device_token) < 20:
                raise ValueError("Invalid device token")

            title = f"New message from {message.sender_name}"
            body = message.message_preview

            data = {
                "chat_id": message.chat_id,
                "sender_id": message.sender_id,
                "sender_name": message.sender_name,
                "notification_id": message.notification_id,
            }

            await self.fcm.send_notification(
                device_token=message.device_token, title=title, body=body, data=data
            )

            await self.redis.mark_as_sent(message.idempotency_key)

            audit_log = AuditLog(
                trace_id=message.notification_id,
                user_id=message.user_id,
                chat_id=message.chat_id,
                sender_name=message.sender_name,
                status=NotificationStatus.SENT,
                metadata=message.metadata,
            )
            await self.db.log_notification(audit_log)

            logger.info(f"Notification {message.notification_id} sent successfully")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            raise

        except Exception as e:
            logger.error(f"Failed to process message: {e}")

            try:
                message_data = json.loads(payload)
                message = NotificationMessage(**message_data)

                await self.redis.mark_as_failed(message.idempotency_key)

                audit_log = AuditLog(
                    trace_id=message.notification_id,
                    user_id=message.user_id,
                    chat_id=message.chat_id,
                    sender_name=message.sender_name,
                    status=NotificationStatus.FAILED,
                    error_message=str(e),
                    metadata=message.metadata,
                )
                await self.db.log_notification(audit_log)

                dlq_message = DlqMessage(
                    original_message=message,
                    failure_reason=str(e),
                    failed_at=datetime.now(timezone.utc).isoformat(),
                )
                await self.rabbitmq.publish_to_dlq(dlq_message)

            except Exception as dlq_error:
                logger.error(f"Failed to handle error: {dlq_error}")

            raise

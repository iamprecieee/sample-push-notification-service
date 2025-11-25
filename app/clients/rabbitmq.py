from aio_pika import connect_robust, Message, DeliveryMode
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel
from typing import Optional
import logging
from app.models import DlqMessage

logger = logging.getLogger(__name__)


class RabbitMqClient:
    """RabbitMQ client for message queue operations"""

    def __init__(
        self,
        rabbitmq_url: str,
        push_queue_name: str,
        failed_queue_name: str,
        prefetch_count: int,
    ):
        self.rabbitmq_url = rabbitmq_url
        self.push_queue_name = push_queue_name
        self.failed_queue_name = failed_queue_name
        self.prefetch_count = prefetch_count
        self.connection: Optional[AbstractRobustConnection] = None
        self.channel: Optional[AbstractRobustChannel] = None

    async def connect(self):
        """Establish RabbitMQ connection"""
        self.connection = await connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=self.prefetch_count)

        # Declare queues
        await self.channel.declare_queue(self.push_queue_name, durable=True)
        await self.channel.declare_queue(self.failed_queue_name, durable=True)

        logger.info("RabbitMQ connection established")

    async def close(self):
        """Close RabbitMQ connection"""
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()

    async def consume_messages(self, callback):
        """Start consuming messages from queue"""
        queue = await self.channel.get_queue(self.push_queue_name)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    await callback(message.body.decode())

    async def publish_to_dlq(self, dlq_message: DlqMessage):
        """Publish failed message to Dead Letter Queue"""
        message_body = dlq_message.model_dump_json().encode()

        message = Message(message_body, delivery_mode=DeliveryMode.PERSISTENT)

        await self.channel.default_exchange.publish(
            message, routing_key=self.failed_queue_name
        )

        logger.debug(
            f"Message published to DLQ: {dlq_message.original_message.idempotency_key}"
        )

    async def health_check(self) -> bool:
        """Health check for RabbitMQ"""
        try:
            if self.connection and not self.connection.is_closed:
                return True
            return False
        except Exception as e:
            logger.error(f"RabbitMQ health check failed: {e}")
            return False

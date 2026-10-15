import aio_pika
import json
import logging
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger("rabbitmq_service")

class RabbitMQService:
    def __init__(self):
        self.connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self.channel: Optional[aio_pika.abc.AbstractChannel] = None
        self.exchange: Optional[aio_pika.abc.AbstractExchange] = None
        self.is_connected: bool = False

    async def connect(self):
        try:
            url = f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/"
            self.connection = await aio_pika.connect_robust(url)
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=50)

            # Declare Dead Letter Exchange & Queue
            dlx_exchange = await self.channel.declare_exchange(
                "fintech.dlx", aio_pika.ExchangeType.DIRECT, durable=True
            )
            dlq = await self.channel.declare_queue(
                settings.QUEUE_DEAD_LETTER, durable=True
            )
            await dlq.bind(dlx_exchange, routing_key="dlq.key")

            # Declare Main Topic Exchange
            self.exchange = await self.channel.declare_exchange(
                settings.EXCHANGE_TRANSACTIONS, aio_pika.ExchangeType.TOPIC, durable=True
            )

            # Declare Main Queues with DLX configuration
            q_args = {
                "x-dead-letter-exchange": "fintech.dlx",
                "x-dead-letter-routing-key": "dlq.key"
            }

            q_audit = await self.channel.declare_queue(
                settings.QUEUE_SETTLEMENT_AUDIT, durable=True, arguments=q_args
            )
            await q_audit.bind(self.exchange, routing_key="transaction.settlement")

            q_fraud = await self.channel.declare_queue(
                settings.QUEUE_HIGH_PRIORITY_FRAUD, durable=True, arguments=q_args
            )
            await q_fraud.bind(self.exchange, routing_key="transaction.fraud.alert")

            self.is_connected = True
            logger.info("Connected to RabbitMQ and declared durable exchanges/queues.")
        except Exception as e:
            logger.warning(f"RabbitMQ connection unavailable ({e}). Operating in memory/mock fallback mode.")
            self.is_connected = False

    async def publish_transaction_event(self, routing_key: str, event_data: Dict[str, Any]):
        if not self.is_connected or not self.exchange:
            logger.debug(f"[MOCK_RABBITMQ] Published to {routing_key}: {event_data.get('id')}")
            return

        try:
            body = json.dumps(event_data).encode("utf-8")
            message = aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json"
            )
            await self.exchange.publish(message, routing_key=routing_key)
        except Exception as e:
            logger.error(f"Failed to publish message to RabbitMQ: {e}")

    async def close(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            self.is_connected = False

rabbitmq_service = RabbitMQService()

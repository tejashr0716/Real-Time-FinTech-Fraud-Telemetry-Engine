import asyncio
import json
import logging
import signal
import uuid
import aio_pika
from app.config import settings
from app.services.database_service import db_service
from app.services.cosmos_service import cosmos_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [FRAUD_SETTLEMENT_WORKER] %(message)s"
)
logger = logging.getLogger("fraud_worker")

class FraudSettlementWorker:
    def __init__(self):
        self.running = False
        self.connection = None
        self.channel = None

    async def start(self):
        self.running = True
        await db_service.connect()
        logger.info("Connected to PostgreSQL / Azure SQL.")

        try:
            url = f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/"
            self.connection = await aio_pika.connect_robust(url)
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=25)

            # Consume from settlement audit queue
            queue_settle = await self.channel.get_queue(settings.QUEUE_SETTLEMENT_AUDIT)
            queue_fraud = await self.channel.get_queue(settings.QUEUE_HIGH_PRIORITY_FRAUD)

            logger.info("Listening for messages on RabbitMQ queues...")

            async def process_settlement(message: aio_pika.abc.AbstractIncomingMessage):
                async with message.process():
                    payload = json.loads(message.body.decode())
                    logger.info(f"Settled transaction {payload.get('transaction_id')}: ${payload.get('amount')}")

            async def process_fraud(message: aio_pika.abc.AbstractIncomingMessage):
                async with message.process():
                    payload = json.loads(message.body.decode())
                    tx_id = payload.get("transaction_id")
                    acc_id = payload.get("account_id")
                    logger.warning(f"🚨 FRAUD ALERT AUDITED: Tx {tx_id} on Account {acc_id}. Score: {payload.get('fraud_score')}")

                    # Persist regulatory audit entry
                    try:
                        await db_service.execute(
                            """INSERT INTO fraud_audit_ledger (transaction_id, account_id, action_taken, risk_factors)
                               VALUES ($1, $2, 'AUTO_BLOCKED', $3)""",
                            uuid.UUID(tx_id), uuid.UUID(acc_id), json.dumps(payload.get("rules_triggered", []))
                        )
                    except Exception as e:
                        logger.error(f"Audit log failed: {e}")

            await queue_settle.consume(process_settlement)
            await queue_fraud.consume(process_fraud)

            while self.running:
                await asyncio.sleep(1.0)

        except Exception as e:
            logger.warning(f"RabbitMQ consumer loop ended or mock mode active: {e}")

    async def stop(self):
        self.running = False
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
        await db_service.close()
        logger.info("Worker shutdown cleanly.")

async def main():
    worker = FraudSettlementWorker()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))
    await worker.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import get_settings
from app.clients import RedisClient, DatabaseClient, FcmClient, RabbitMqClient
from app.worker import MessageProcessor
from app.api.routes import router

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    settings = get_settings()

    logger.info("Initializing clients...")

    redis_client = RedisClient(
        redis_url=settings.redis_url, idempotency_ttl=settings.idempotency_ttl_seconds
    )
    await redis_client.connect()
    app.state.redis = redis_client

    database_client = DatabaseClient(database_url=settings.database_url)
    await database_client.connect()
    app.state.database = database_client

    fcm_client = FcmClient(
        project_id=settings.fcm_project_id,
        credentials_path=settings.google_application_credentials,
    )
    await fcm_client.initialize()
    app.state.fcm = fcm_client

    rabbitmq_client = RabbitMqClient(
        rabbitmq_url=settings.rabbitmq_url,
        push_queue_name=settings.push_queue_name,
        failed_queue_name=settings.failed_queue_name,
        prefetch_count=settings.prefetch_count,
    )
    await rabbitmq_client.connect()
    app.state.rabbitmq = rabbitmq_client

    processor = MessageProcessor(
        redis_client=redis_client,
        database_client=database_client,
        fcm_client=fcm_client,
        rabbitmq_client=rabbitmq_client,
    )

    worker_task = asyncio.create_task(
        rabbitmq_client.consume_messages(processor.process_message)
    )
    app.state.worker_task = worker_task

    logger.info("Application started successfully")

    yield

    logger.info("Shutting down...")

    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    await rabbitmq_client.close()
    await fcm_client.close()
    await database_client.close()
    await redis_client.close()

    logger.info("Shutdown complete")


app = FastAPI(
    title="Push Notification Service",
    description="FastAPI push notification microservice",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Push Notification Service",
        "version": "1.0.0",
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.server_port, reload=False)

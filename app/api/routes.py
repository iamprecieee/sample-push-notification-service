from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone
import time
from app.models import HealthCheckResponse, ServiceHealth, HealthStatus

router = APIRouter()


@router.get("/health", response_model=dict)
async def health_check(request: Request):
    """Comprehensive health check endpoint"""
    redis = request.app.state.redis
    db = request.app.state.database
    rabbitmq = request.app.state.rabbitmq

    checks = {}

    start = time.time()
    db_healthy = await db.health_check()
    db_time = int((time.time() - start) * 1000)

    checks["database"] = ServiceHealth(
        status=HealthStatus.HEALTHY if db_healthy else HealthStatus.UNHEALTHY,
        response_time_ms=db_time if db_healthy else None,
        error=None if db_healthy else "Database connection failed",
    )

    start = time.time()
    redis_healthy = await redis.ping()
    redis_time = int((time.time() - start) * 1000)

    checks["cache_service"] = ServiceHealth(
        status=HealthStatus.HEALTHY if redis_healthy else HealthStatus.UNHEALTHY,
        response_time_ms=redis_time if redis_healthy else None,
        error=None if redis_healthy else "Redis connection failed",
    )

    start = time.time()
    rabbitmq_healthy = await rabbitmq.health_check()
    rabbitmq_time = int((time.time() - start) * 1000)

    checks["message_broker"] = ServiceHealth(
        status=HealthStatus.HEALTHY if rabbitmq_healthy else HealthStatus.UNHEALTHY,
        response_time_ms=rabbitmq_time if rabbitmq_healthy else None,
        error=None if rabbitmq_healthy else "RabbitMQ connection failed",
    )

    critical_unhealthy = not (db_healthy and redis_healthy and rabbitmq_healthy)

    if critical_unhealthy:
        overall_status = HealthStatus.UNHEALTHY
        message = "Service unhealthy"
    else:
        overall_status = HealthStatus.HEALTHY
        message = "All systems operational"

    response = HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks=checks,
    )

    return {"success": True, "data": response.model_dump(), "message": message}


@router.get("/status/{notification_id}")
async def get_notification_status(notification_id: str, request: Request):
    """Get status of a notification by ID"""
    db = request.app.state.database

    status = await db.get_notification_status(notification_id)

    if not status:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"success": True, "data": status, "message": "Status retrieved"}

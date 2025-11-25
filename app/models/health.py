from pydantic import BaseModel
from typing import Dict, Optional
from enum import Enum


class HealthStatus(str, Enum):
    """Overall health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseModel):
    """Individual service health check"""
    status: HealthStatus
    response_time_ms: Optional[int] = None
    circuit_breaker: Optional[str] = None
    error: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Complete health check response"""
    status: HealthStatus
    timestamp: str
    checks: Dict[str, ServiceHealth]
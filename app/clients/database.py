import asyncpg
from typing import Optional
import logging
import json
from app.models import AuditLog

logger = logging.getLogger(__name__)


class DatabaseClient:
    """PostgreSQL client for audit logging"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create database connection pool"""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10
        )
        logger.info("PostgreSQL connection pool created")

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()

    async def log_notification(self, audit_log: AuditLog):
        """Write audit log entry"""
        query = """
            INSERT INTO audit_logs (
                trace_id, user_id, notification_type, chat_id,
                sender_name, status, error_message, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                audit_log.trace_id,
                audit_log.user_id,
                audit_log.notification_type,
                audit_log.chat_id,
                audit_log.sender_name,
                audit_log.status.value,
                audit_log.error_message,
                json.dumps(audit_log.metadata)
            )
        
        logger.debug(f"Audit log written for {audit_log.trace_id}")

    async def get_notification_status(self, trace_id: str) -> Optional[dict]:
        """Get notification status by trace ID"""
        query = """
            SELECT trace_id, user_id, notification_type, chat_id,
                   sender_name, status, error_message, metadata, created_at
            FROM audit_logs
            WHERE trace_id = $1
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, trace_id)
            if row:
                return dict(row)
        
        return None

    async def health_check(self) -> bool:
        """Health check for PostgreSQL"""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
# Push Notification Service (FastAPI)

A production-ready push notification microservice built with FastAPI. Consumes messages from RabbitMQ, tracks idempotency with Redis, sends notifications via Firebase Cloud Messaging (FCM), and maintains audit logs in PostgreSQL.

## Features

- **Idempotency**: Prevents duplicate message processing using Redis
- **Dead Letter Queue**: Failed messages routed to DLQ for manual review
- **Audit Logging**: Complete notification lifecycle tracking in PostgreSQL
- **Health Checks**: Comprehensive health endpoint monitoring all dependencies
- **High Throughput**: Concurrent message processing with configurable worker limits
- **Production Ready**: Docker support, proper error handling, and logging

## Project Structure

```
push-service-python/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration management
│   ├── worker.py            # Message processor
│   ├── models/              # Data models
│   │   ├── message.py
│   │   ├── audit.py
│   │   └── health.py
│   ├── clients/             # External service clients
│   │   ├── redis_client.py
│   │   ├── database.py
│   │   ├── fcm.py
│   │   └── rabbitmq.py
│   └── api/
│       └── routes.py        # API routes
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── schema.sql
└── .env.example
```

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (for local development)
- Firebase Project with service account credentials

## Quick Start

### 1. Get Firebase Credentials

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project (or create one)
3. Navigate to **Project Settings** → **Service Accounts**
4. Click **Generate New Private Key**
5. Save the file as `service-account.json` in the project root

```bash
# Verify the file
cat service-account.json | python -c "import json, sys; print(json.load(sys.stdin)['project_id'])"
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your Firebase project ID:

```bash
FCM_PROJECT_ID=your-actual-project-id
```

### 3. Start All Services

```bash
docker-compose up --build
```

This starts:
- RabbitMQ (ports 5672, 15672)
- Redis (port 6379)
- PostgreSQL (port 5432)
- Push Service (port 8080)

### 4. Verify It's Working

```bash
curl http://localhost:8080/health | python -m json.tool
```

Expected response:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2025-11-25T...",
    "checks": {
      "database": {"status": "healthy", "response_time_ms": 5},
      "cache_service": {"status": "healthy", "response_time_ms": 2},
      "message_broker": {"status": "healthy", "response_time_ms": 3}
    }
  },
  "message": "All systems operational"
}
```

## Message Format

Send messages to the `push_notifications` queue in this format:

```json
{
  "notification_id": "notif_12345",
  "idempotency_key": "unique_key_001",
  "user_id": "user_123",
  "chat_id": "chat_456",
  "sender_id": "user_789",
  "sender_name": "John Doe",
  "message_preview": "Hey, how are you?",
  "device_token": "fcm_device_token_xyz123",
  "priority": 1,
  "metadata": {
    "source": "mobile_app"
  },
  "created_by": "user_789",
  "timestamp": "2025-11-25T10:30:00Z"
}
```

## Sending Test Notifications

### Using RabbitMQ Management UI

1. Open http://localhost:15672 (guest/guest)
2. Go to **Queues** → **push_notifications** → **Publish message**
3. Paste the message JSON above (update `device_token` with a real FCM token)
4. Click **Publish message**


## API Endpoints

### Health Check

```bash
GET http://localhost:8080/health
```

Returns health status of all services.

### Get Notification Status

```bash
GET http://localhost:8080/status/{notification_id}
```

Returns the status of a specific notification.

## Configuration

All configuration via environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `RABBITMQ_URL` | RabbitMQ connection string | `amqp://guest:guest@localhost:5672/` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `FCM_PROJECT_ID` | Firebase project ID | *required* |
| `WORKER_CONCURRENCY` | Max concurrent workers | `4` |
| `PREFETCH_COUNT` | RabbitMQ prefetch count | `10` |

## Integration with Backend (Sample)

When a new message is created in your system, publish a notification message to RabbitMQ:

```python
# In your messaging service
async def send_message(chat_id: str, sender: User, content: str):
    # Save message to database
    message = await save_message(chat_id, sender.id, content)
    
    # Get recipient's device token
    recipient = await get_chat_recipient(chat_id, exclude=sender.id)
    device_token = await get_user_device_token(recipient.id)
    
    # Publish push notification event
    notification_message = {
        "notification_id": f"notif_{message.id}",
        "idempotency_key": f"msg_{message.id}",
        "user_id": recipient.id,
        "chat_id": chat_id,
        "sender_id": sender.id,
        "sender_name": sender.name,
        "message_preview": content[:50],  # First 50 chars
        "device_token": device_token,
        "priority": 1,
        "metadata": {"message_id": message.id},
        "created_by": sender.id,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await publish_to_rabbitmq("push_notifications", notification_message)
```

## Monitoring

### View Logs

```bash
docker-compose logs -f push-service
```

### Check Queue Status

```bash
# RabbitMQ Management UI
open http://localhost:15672

# Check queue sizes
docker exec push-service-rabbitmq rabbitmqctl list_queues
```

### Query Audit Logs

```bash
docker exec -it push-service-postgres psql -U postgres -d notifications_db

# Get recent notifications
SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 10;

# Count by status
SELECT status, COUNT(*) FROM audit_logs GROUP BY status;
```
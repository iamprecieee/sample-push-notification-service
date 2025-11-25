import httpx
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class FcmClient:
    """Firebase Cloud Messaging client"""

    def __init__(self, project_id: str, credentials_path: str):
        self.project_id = project_id
        self.credentials_path = credentials_path
        self.credentials: Optional[service_account.Credentials] = None
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def initialize(self):
        """Initialize FCM credentials"""
        scopes = ["https://www.googleapis.com/auth/firebase.messaging"]
        self.credentials = service_account.Credentials.from_service_account_file(
            self.credentials_path, scopes=scopes
        )
        logger.info("FCM client initialized")

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()

    def _get_access_token(self) -> str:
        """Get OAuth2 access token"""
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        return self.credentials.token

    async def send_notification(
        self, device_token: str, title: str, body: str, data: dict
    ):
        """Send push notification via FCM"""
        url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"

        access_token = self._get_access_token()

        payload = {
            "message": {
                "token": device_token,
                "notification": {"title": title, "body": body},
                "data": data,
            }
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        response = await self.http_client.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            logger.info("Push notification sent successfully")
        else:
            error_text = response.text
            logger.error(f"FCM request failed: {error_text}")
            raise Exception(f"FCM request failed: {error_text}")

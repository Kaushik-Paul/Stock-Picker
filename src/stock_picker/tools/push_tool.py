from crewai.tools import BaseTool
import json
from pathlib import Path
from typing import Type
from pydantic import BaseModel, Field
import os
from mailjet_rest import Client

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EMAIL_STATUS_PATH = PROJECT_ROOT / "output/email_status.json"


class MailJetNotification(BaseModel):
    """A message to be sent to the user"""
    subject: str = Field(..., description="The subject of the email to be sent to the user.")
    message: str = Field(..., description="The email body to be sent to the user.")
    to_user: str = Field(..., description="The email address of the user to send the email.")

class MailJetNotificationTool(BaseTool):
    

    name: str = "Send an Email"
    description: str = (
        "This tool sends an email to the user using MailJet."
    )
    args_schema: Type[BaseModel] = MailJetNotification

    def _run(self, subject: str, message: str, to_user: str) -> str:
        api_key = os.getenv("MAILJET_API_KEY")
        api_secret = os.getenv("MAILJET_API_SECRET")
        from_email = os.getenv("MAILJET_FROM_EMAIL")
        missing = [
            name for name, value in {
                "MAILJET_API_KEY": api_key,
                "MAILJET_API_SECRET": api_secret,
                "MAILJET_FROM_EMAIL": from_email,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing MailJet environment variables: {', '.join(missing)}")

        mailjet = Client(auth=(api_key, api_secret), version='v3.1')
        data = {
            'Messages': [
                {
                    "From": {
                        "Email": from_email,
                        "Name": "Kaushik Paul"
                    },
                    "To": [
                        {
                            "Email": to_user,
                            "Name": "User Name"
                        }
                    ],
                    "Subject": subject,
                    "HTMLPart": message,
                }
            ]
        }
        result = mailjet.send.create(data=data)
        status_code = getattr(result, "status_code", None)
        response_body = result.json() if hasattr(result, "json") else {}
        if status_code is None or status_code >= 400:
            raise RuntimeError(
                f"MailJet send failed with status {status_code}: {response_body}"
            )

        messages = response_body.get("Messages", []) if isinstance(response_body, dict) else []
        message_info = messages[0] if messages else {}
        message_status = message_info.get("Status")
        if message_status and str(message_status).lower() != "success":
            raise RuntimeError(
                f"MailJet accepted the request but did not send the email: {response_body}"
            )

        status = {
            "notification": "ok",
            "provider": "mailjet",
            "status_code": status_code,
            "message_status": message_status,
            "to": to_user,
        }
        EMAIL_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        EMAIL_STATUS_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")
        return json.dumps(status)

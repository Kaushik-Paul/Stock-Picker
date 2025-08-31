from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os
import requests
from mailjet_rest import Client


class MailJetNotification(BaseModel):
    """A message to be sent to the user"""
    subject: str = Field(..., description="The subject of the email to be sent to the user.")
    message: str = Field(..., description="The email body to be sent to the user.")
    to_user: str = Field(..., description="The email address of the user to send the email.")

class MailJetNotificationTool(BaseTool):
    

    name: str = "Send a Email"
    description: str = (
        "This tool is used to send a email to the user."
    )
    args_schema: Type[BaseModel] = MailJetNotification

    def _run(self, subject: str, message: str, to_user: str) -> str:
        api_key = os.getenv("MAILJET_API_KEY")
        api_secret = os.getenv("MAILJET_API_SECRET")
        from_email = os.getenv("MAILJET_FROM_EMAIL")
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
                    "TextPart": message,
                }
            ]
        }
        result = mailjet.send.create(data=data)
        return '{"notification": "ok"}'
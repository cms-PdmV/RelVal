"""
Module that handles all email notifications
"""
import json
from core_lib.utils.emailer import Emailer as BaseEmailer
from core_lib.utils.global_config import Config


class Emailer(BaseEmailer):
    """
    Emailer sends email notifications to users
    """

    def __init__(self, credentials_file: str):
        self.credentials = credentials_file
        username, password = self.__retrieve_credentials()
        super().__init__(username=username, password=password)

    def __retrieve_credentials(self):
        """
        Read credentials and connect to SMTP file
        """
        with open(self.credentials) as json_file:
            credentials = json.load(json_file)
            return credentials["username"], credentials["password"]

    def send(self, subject, body, recipients):
        body = body.strip() + "\n\nSincerely,\nRelVal Machine"
        if Config.get("development"):
            subject = f"[RelVal-DEV] {subject}"
        else:
            subject = f"[RelVal] {subject}"

        super().send(subject, body, recipients)

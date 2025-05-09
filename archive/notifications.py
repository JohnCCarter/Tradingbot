"""
Notifieringar för Tradingbot
"""
import smtplib
from email.mime.text import MIMEText
import requests

class EmailNotifier:
    def __init__(self, smtp_server, smtp_port, sender, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender = sender
        self.password = password

    def send(self, receiver, subject, body):
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.sender
        msg['To'] = receiver
        with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
            server.login(self.sender, self.password)
            server.sendmail(self.sender, receiver, msg.as_string())

class SlackNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
    def send(self, message):
        requests.post(self.webhook_url, json={"text": message})

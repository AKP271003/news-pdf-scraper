#!/usr/bin/env python3
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import logging
from typing import Optional
from app.config import settings

#Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_pass = settings.SMTP_PASS

    def send_email_with_attachment(self, to_email: str, subject: str, 
                                 body: str, attachment_path: str) -> bool:

        try:
            #Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            #Add attachment
            if os.path.exists(attachment_path):
                with open(attachment_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())

                encoders.encode_base64(part)

                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(attachment_path)}'
                )

                msg.attach(part)
            else:
                logger.error(f"Attachment file not found: {attachment_path}")
                return False

            #Send email
            context = ssl.create_default_context()

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.smtp_user, to_email, msg.as_string())

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_news_pdf(self, to_email: str, pdf_path: str, 
                      categories: list) -> bool:

        from datetime import datetime

        categories_text = ", ".join(categories).title()
        subject = f"Indian Express News Summary - {datetime.now().strftime('%B %d, %Y')}"

        body = f"""Hello,

Please find attached your personalized Indian Express news summary for {datetime.now().strftime('%B %d, %Y')}.

Categories included: {categories_text}

Best regards,
News PDF Scraper
"""

        return self.send_email_with_attachment(to_email, subject, body, pdf_path)

    def test_email_configuration(self) -> bool:
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_pass)

            logger.info("Email configuration test successful")
            return True

        except Exception as e:
            logger.error(f"Email configuration test failed: {e}")
            return False

email_service = EmailService()
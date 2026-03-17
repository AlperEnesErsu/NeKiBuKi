from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


class Notifier:
    def send_desktop(self, title: str, message: str) -> None:
        try:
            from plyer import notification

            notification.notify(title=title, message=message, timeout=10)
        except Exception:
            # Desktop notification is optional; fallback to console output.
            print(f"[DESKTOP BILDIRIM] {title} - {message}")

    def send_email(self, to_email: str, subject: str, message: str) -> bool:
        smtp_host = os.getenv("NEKIBUKI_SMTP_HOST")
        smtp_port = int(os.getenv("NEKIBUKI_SMTP_PORT", "587"))
        smtp_user = os.getenv("NEKIBUKI_SMTP_USER")
        smtp_pass = os.getenv("NEKIBUKI_SMTP_PASS")
        smtp_from = os.getenv("NEKIBUKI_SMTP_FROM", smtp_user or "")

        if not smtp_host or not smtp_user or not smtp_pass or not smtp_from:
            return False

        email = EmailMessage()
        email["From"] = smtp_from
        email["To"] = to_email
        email["Subject"] = subject
        email.set_content(message)

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(email)
            return True
        except Exception:
            return False

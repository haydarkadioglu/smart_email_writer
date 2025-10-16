import os
from datetime import datetime
from typing import List

import pandas as pd


class ExcelLogger:
    def __init__(self, log_filepath: str = "logs/sent_emails.xlsx") -> None:
        self.log_filepath = log_filepath
        directory = os.path.dirname(self.log_filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def append(
        self,
        sender_email: str,
        recipient_email: str,
        subject: str,
        body: str,
        provider: str,
    ) -> None:
        row = {
            "timestamp": datetime.utcnow().isoformat(),
            "provider": provider,
            "sender": sender_email,
            "recipient": recipient_email,
            "subject": subject,
            "body": body,
        }

        df_new = pd.DataFrame([row])
        if os.path.exists(self.log_filepath):
            try:
                df_old = pd.read_excel(self.log_filepath)
                df_all = pd.concat([df_old, df_new], ignore_index=True)
            except Exception:
                # If file is corrupted/unreadable, start fresh
                df_all = df_new
        else:
            df_all = df_new

        df_all.to_excel(self.log_filepath, index=False)

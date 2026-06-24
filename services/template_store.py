import json
import os
import uuid
from typing import Any, Dict, List


class TemplateStore:
    def __init__(self, filepath: str = "config/templates.json") -> None:
        self.filepath = filepath
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def load_all(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.filepath):
            # Write default templates
            default_templates = [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Cold Outreach",
                    "subject": "Collaboration Opportunity - {company}",
                    "body": "Dear {name},\n\nI hope this email finds you well.\n\nI have been following {company}'s work in the industry, particularly your recent updates. I see that you are dealing with {description}. Our team has built solutions that help companies streamline these processes.\n\nI would love to have a brief 10-minute call next week to see if there is a mutual fit.\n\nBest regards,\n{my_name}",
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "Follow-Up Meeting",
                    "subject": "Follow-up: SEW AI Discussion",
                    "body": "Hi {name},\n\nThank you for taking the time to speak with me earlier regarding {description}.\n\nAs discussed, I've attached more details about our services. Let me know if next Thursday at 2 PM works for a quick follow-up to discuss the next steps.\n\nLooking forward to hearing from you.\n\nBest,\n{my_name}",
                },
                {
                    "id": str(uuid.uuid4()),
                    "title": "Project Update",
                    "subject": "Status Update: {description}",
                    "body": "Hello {name},\n\nI'm writing to provide a quick update on {description}.\n\nEverything is progressing according to schedule. We are currently finalizing the key milestones. I will share a complete report by the end of this week.\n\nLet me know if you have any questions.\n\nRegards,\n{my_name}",
                }
            ]
            self.save_all(default_templates)
            return default_templates
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_all(self, templates: List[Dict[str, Any]]) -> None:
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)

    def add(self, title: str, subject: str, body: str) -> Dict[str, Any]:
        templates = self.load_all()
        new_template = {
            "id": str(uuid.uuid4()),
            "title": title,
            "subject": subject,
            "body": body,
        }
        templates.append(new_template)
        self.save_all(templates)
        return new_template

    def update(self, template_id: str, title: str, subject: str, body: str) -> bool:
        templates = self.load_all()
        for t in templates:
            if t["id"] == template_id:
                t["title"] = title
                t["subject"] = subject
                t["body"] = body
                self.save_all(templates)
                return True
        return False

    def delete(self, template_id: str) -> bool:
        templates = self.load_all()
        filtered = [t for t in templates if t["id"] != template_id]
        if len(filtered) < len(templates):
            self.save_all(filtered)
            return True
        return False

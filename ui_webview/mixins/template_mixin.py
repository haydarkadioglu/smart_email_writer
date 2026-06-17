from typing import Dict, List, Any, Optional

class TemplateMixin:
    def list_templates(self) -> Dict[str, Any]:
        try:
            templates = self.template_store.load_all()
            mapped = []
            for t in templates:
                mapped.append({
                    "id": t.get("id"),
                    "name": t.get("title") or t.get("name"),
                    "subject": t.get("subject"),
                    "body": t.get("body"),
                    "category": t.get("category", "General")
                })
            return {"success": True, "templates": mapped}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_template(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            template_id = payload.get("id")
            title = payload.get("name") or payload.get("title") or "Untitled Template"
            subject = payload.get("subject", "")
            body = payload.get("body", "")
            category = payload.get("category", "General")

            templates = self.template_store.load_all()
            if template_id:
                # Update existing template
                for t in templates:
                    if t["id"] == template_id:
                        t["title"] = title
                        t["subject"] = subject
                        t["body"] = body
                        t["category"] = category
                        break
                self.template_store.save_all(templates)
            else:
                # Add new template
                import uuid
                new_t = {
                    "id": str(uuid.uuid4()),
                    "title": title,
                    "subject": subject,
                    "body": body,
                    "category": category
                }
                templates.append(new_t)
                self.template_store.save_all(templates)
                
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_template(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.save_template(payload)

    def delete_template(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            template_id = payload.get("id")
            if not template_id:
                return {"success": False, "error": "Template ID is required"}
            self.template_store.delete(template_id)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_template(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            template_id = payload.get("id")
            templates = self.template_store.load_all()
            for t in templates:
                if t["id"] == template_id:
                    return {
                        "success": True,
                        "template": {
                            "id": t.get("id"),
                            "name": t.get("title") or t.get("name"),
                            "subject": t.get("subject"),
                            "body": t.get("body"),
                            "category": t.get("category", "General")
                        }
                    }
            return {"success": False, "error": "Template not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

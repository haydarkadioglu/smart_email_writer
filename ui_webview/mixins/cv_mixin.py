import json
from typing import Dict, Any


class CvMixin:
    """CV / Resume parsing to auto-fill profile fields."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

    def parse_cv(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a CV/Resume file and extract profile fields using AI.
        payload: { "file_path": str }
        """
        try:
            file_path = payload.get("file_path", "")
            if not file_path:
                return {"success": False, "error": "No file path provided"}

            from pathlib import Path
            p = Path(file_path)
            if not p.exists():
                return {"success": False, "error": "File not found"}

            ext = p.suffix.lower()
            if ext not in self.SUPPORTED_EXTENSIONS:
                return {"success": False, "error": f"Unsupported file type: {ext}. Use PDF, DOCX, or TXT."}

            text = self._extract_text(p, ext)
            if not text.strip():
                return {"success": False, "error": "Could not extract text from file"}

            profile_data = self._ai_extract_profile(text)
            return {"success": True, "profile": profile_data}

        except json.JSONDecodeError:
            return {"success": False, "error": "AI returned invalid JSON"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Text extraction ────────────────────────────────────────────────────

    def _extract_text(self, path, ext: str) -> str:
        if ext == ".pdf":
            return self._extract_pdf(path)
        elif ext == ".docx":
            return self._extract_docx(path)
        else:
            return path.read_text(encoding="utf-8", errors="ignore")

    def _extract_pdf(self, path) -> str:
        try:
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except ImportError:
            raise RuntimeError("pdfplumber not installed. Run: pip install pdfplumber")

    def _extract_docx(self, path) -> str:
        try:
            import docx
            doc = docx.Document(str(path))
            return "\n".join(para.text for para in doc.paragraphs)
        except ImportError:
            raise RuntimeError("python-docx not installed. Run: pip install python-docx")

    # ── AI extraction ──────────────────────────────────────────────────────

    def _ai_extract_profile(self, text: str) -> Dict[str, str]:
        prompt = (
            "Extract profile information from the following CV/resume text. "
            "Return ONLY a JSON object (no markdown, no explanation) with these exact keys: "
            "name, email, phone, company, role, website, summary. "
            "Use empty string \"\" for any field not found.\n\n"
            "CV Text:\n" + text[:4000]
        )

        settings   = self.settings_store.load()
        provider   = settings.get("ai_provider", "gemini")
        model_name = settings.get(provider + "_model", "")

        ai_client = self._get_ai_client(provider, model_name)
        raw = ai_client._call_raw(prompt)
        raw = raw.strip().strip("```json").strip("```").strip()
        return json.loads(raw)

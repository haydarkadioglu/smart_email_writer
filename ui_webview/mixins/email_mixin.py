# email_mixin.py is now split into:
#   ai_mixin.py   – AI client, email generation / refinement, usage logging
#   smtp_mixin.py – SMTP send, test, file picker
#
# This file is kept as a compatibility re-export so any external references
# (e.g. tests, build scripts) still resolve without changes.

from ui_webview.mixins.ai_mixin import AiMixin
from ui_webview.mixins.smtp_mixin import SmtpMixin


class EmailMixin(AiMixin, SmtpMixin):
    """Backward-compatible alias combining AiMixin and SmtpMixin."""
    pass

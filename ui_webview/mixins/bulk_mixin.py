# bulk_mixin.py is now split into:
#   bulk_file_mixin.py – file selection, parsing, preview, AI generation
#   bulk_send_mixin.py – background bulk sending, thread control, per-email dispatch
#
# This shim maintains backward compatibility.

from ui_webview.mixins.bulk_file_mixin import BulkFileMixin
from ui_webview.mixins.bulk_send_mixin import BulkSendMixin


class BulkMixin(BulkFileMixin, BulkSendMixin):
    """Backward-compatible alias combining BulkFileMixin and BulkSendMixin."""
    pass

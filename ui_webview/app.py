import threading
import webview
from pathlib import Path
from typing import Optional

from services.email_sender import EmailSender
from services.bulk_email_sender import BulkEmailSender
from services.file_parser import FileParser
from services.excel_logger import ExcelLogger
from services.profile_store import ProfileStore
from services.settings_store import SettingsStore
from services.template_store import TemplateStore
from services.history_store import HistoryStore
from services.spam_analyzer import SpamAnalyzer

# Import mixins
from ui_webview.mixins.config_mixin import ConfigMixin
from ui_webview.mixins.template_mixin import TemplateMixin
from ui_webview.mixins.history_mixin import HistoryMixin
from ui_webview.mixins.email_mixin import EmailMixin
from ui_webview.mixins.bulk_mixin import BulkMixin


class WebViewAPI(ConfigMixin, TemplateMixin, HistoryMixin, EmailMixin, BulkMixin):
    """
    Bridge class exposed to the JS front-end via pywebview.

    IMPORTANT: pywebview's `get_functions` recursively inspects every attribute
    returned by `dir()`.  If it encounters a `webview.Window` it will try to
    access `window.dom.body` *before* the window is open, which raises
    WebViewException.

    Fix: override `__dir__` so only callable public methods are visible to
    pywebview's introspector.  The window reference is stored in a plain
    dict slot (object.__setattr__ bypass) so it is never enumerated.
    """

    # Names pywebview's introspector MUST NOT walk into.
    # pywebview recurses into every non-callable public attr that has __module__,
    # so we must hide the Window reference and all service objects.
    _PRIVATE_ATTRS = frozenset({
        "_window_ref",
        "window",          # webview.Window — triggers dom.body before window opens
        "set_window",      # internal helper, not a JS API method
        "email_sender", "bulk_email_sender", "file_parser",
        "excel_logger", "profile_store", "settings_store",
        "template_store", "history_store", "spam_analyzer",
        "bulk_thread", "stop_bulk_sending",
    })

    def __init__(self) -> None:
        # Store service objects directly (fine, we guard them in __dir__)
        self.email_sender       = EmailSender()
        self.bulk_email_sender  = BulkEmailSender()
        self.file_parser        = FileParser()
        self.excel_logger       = ExcelLogger()
        self.profile_store      = ProfileStore()
        self.settings_store     = SettingsStore()
        self.template_store     = TemplateStore()
        self.history_store      = HistoryStore()
        self.spam_analyzer      = SpamAnalyzer()
        self.bulk_thread: Optional[threading.Thread] = None
        self.stop_bulk_sending  = False
        # Window stored separately so __dir__ can hide it
        object.__setattr__(self, "_window_ref", None)

    # ── Window accessor ────────────────────────────────────────────────────
    @property
    def window(self) -> Optional[webview.Window]:
        return object.__getattribute__(self, "_window_ref")

    @window.setter
    def window(self, w: webview.Window) -> None:
        object.__setattr__(self, "_window_ref", w)

    def set_window(self, w: webview.Window) -> None:
        self.window = w

    # ── Hide private attrs from pywebview's introspector ──────────────────
    def __dir__(self):
        """Return only public callable methods so pywebview doesn't recurse
        into service objects or the window reference."""
        return [
            name for name in super().__dir__()
            if not name.startswith("_")
            and name not in self._PRIVATE_ATTRS
        ]


def apply_dark_titlebar(window) -> None:
    """Apply native Immersive Dark Mode to Windows title bar using Win32 API."""
    import sys
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
        # get HWND pointer
        hwnd_val = window.native.Handle.ToInt32()
        hwnd = wintypes.HWND(hwnd_val)
        value = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )
    except Exception as e:
        print(f"[Warning] Failed to set immersive dark mode title bar: {e}")


def run_app():
    current_dir    = Path(__file__).parent
    index_path     = current_dir / "templates" / "index.html"

    # pywebview needs a file:// URL on Windows
    url = index_path.as_uri()          # e.g. file:///F:/code/.../index.html

    api    = WebViewAPI()
    window = webview.create_window(
        title     = "Smart Email Writer ✨",
        url       = url,
        js_api    = api,
        width     = 1280,
        height    = 860,
        min_size  = (1000, 700),
        resizable = True,
        background_color = '#0d0f12',
    )
    api.set_window(window)

    # Register the event to apply immersive dark title bar
    window.events.shown += lambda: apply_dark_titlebar(window)

    webview.start(debug=False)


if __name__ == "__main__":
    run_app()

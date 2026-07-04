import os
import sys
import atexit
from dotenv import load_dotenv

from ui_webview.app import run_app

# Load environment variables from .env and then .env.local (local overrides)
load_dotenv(dotenv_path=".env", override=False)
load_dotenv(dotenv_path=".env.local", override=False)


# ── Suppress harmless pythonnet shutdown traceback ──────────────────────────
# pythonnet's atexit callback raises KeyboardInterrupt during .NET unload
# when the process is terminating. This is a known pythonnet bug and does not
# affect functionality. We silence it to avoid confusing the user.
def _suppress_pythonnet_unload() -> None:
    try:
        import pythonnet
        import clr_loader  # noqa: F401 – ensure it's imported before patching

        original_unload = getattr(pythonnet, "unload", None)
        if original_unload is None:
            return

        def _safe_unload() -> None:
            try:
                original_unload()
            except (KeyboardInterrupt, Exception):
                pass  # Swallow the spurious error silently

        # Re-register at the front of the atexit queue so our wrapper runs first
        atexit.unregister(original_unload)
        atexit.register(_safe_unload)
    except Exception:
        pass  # If pythonnet isn't installed / importable, nothing to do


_suppress_pythonnet_unload()
# ────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    run_app()

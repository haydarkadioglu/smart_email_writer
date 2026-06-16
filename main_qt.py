"""
Main entry point for Qt6 GUI application
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(dotenv_path=".env", override=False)
load_dotenv(dotenv_path=".env.local", override=False)

from PyQt6.QtWidgets import QApplication
from gui_qt.main_window import MainWindow


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Smart Email Writer")
    app.setOrganizationName("Smart Email Writer")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

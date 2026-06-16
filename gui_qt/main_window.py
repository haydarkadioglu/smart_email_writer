"""
Main Window for Smart Email Writer Qt6 GUI
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
    QStatusBar, QMenuBar, QMenu, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon
from pathlib import Path

from .single_email_tab import SingleEmailTab
from .bulk_email_tab import BulkEmailTab
from .profile_tab import ProfileTab
from .settings_tab import SettingsTab
from .logs_tab import LogsTab


class MainWindow(QMainWindow):
    """Main application window with tabbed interface"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Email Writer ✨ - Qt6 Desktop Edition")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Load stylesheet
        self.load_stylesheet()
        
        # Setup UI
        self.setup_menubar()
        self.setup_tabs()
        self.setup_statusbar()
        
        # Center window on screen
        self.center_on_screen()
        
    def load_stylesheet(self):
        """Load the modern dark theme stylesheet"""
        try:
            style_path = Path(__file__).parent / "styles" / "modern_dark.qss"
            with open(style_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Failed to load stylesheet: {e}")
    
    def setup_menubar(self):
        """Setup the menu bar"""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("📁 File")
        
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_current_tab)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("❌ Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View Menu
        view_menu = menubar.addMenu("👁️ View")
        
        theme_action = QAction("🎨 Toggle Theme (Coming Soon)", self)
        theme_action.setEnabled(False)
        view_menu.addAction(theme_action)
        
        # Help Menu
        help_menu = menubar.addMenu("❓ Help")
        
        about_action = QAction("ℹ️ About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        docs_action = QAction("📚 Documentation", self)
        docs_action.triggered.connect(self.show_docs)
        help_menu.addAction(docs_action)
    
    def setup_tabs(self):
        """Setup the tabbed interface"""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        layout.addWidget(self.tabs)
        
        # Create tabs
        try:
            self.single_email_tab = SingleEmailTab()
            self.tabs.addTab(self.single_email_tab, "✉️ Single Email")
        except Exception as e:
            print(f"Error creating Single Email tab: {e}")
            self.tabs.addTab(QWidget(), "✉️ Single Email")
        
        try:
            self.bulk_email_tab = BulkEmailTab()
            self.tabs.addTab(self.bulk_email_tab, "📧 Bulk Email")
        except Exception as e:
            print(f"Error creating Bulk Email tab: {e}")
            self.tabs.addTab(QWidget(), "📧 Bulk Email")
        
        try:
            self.profile_tab = ProfileTab()
            self.tabs.addTab(self.profile_tab, "👤 Profile")
        except Exception as e:
            print(f"Error creating Profile tab: {e}")
            self.tabs.addTab(QWidget(), "👤 Profile")
        
        try:
            self.settings_tab = SettingsTab()
            self.tabs.addTab(self.settings_tab, "⚙️ Settings")
        except Exception as e:
            print(f"Error creating Settings tab: {e}")
            self.tabs.addTab(QWidget(), "⚙️ Settings")
        
        try:
            self.logs_tab = LogsTab()
            self.tabs.addTab(self.logs_tab, "📊 Logs")
        except Exception as e:
            print(f"Error creating Logs tab: {e}")
            self.tabs.addTab(QWidget(), "📊 Logs")
    
    def setup_statusbar(self):
        """Setup the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Connection indicator
        self.connection_label = QLabel("🟢 Connected")
        self.status_bar.addPermanentWidget(self.connection_label)
        
        # Version info
        version_label = QLabel("v1.0.0")
        self.status_bar.addPermanentWidget(version_label)
    
    def center_on_screen(self):
        """Center the window on screen"""
        from PyQt6.QtGui import QScreen
        screen = QScreen.availableGeometry(self.screen())
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def refresh_current_tab(self):
        """Refresh the current tab"""
        current_index = self.tabs.currentIndex()
        tab_name = self.tabs.tabText(current_index)
        self.status_label.setText(f"Refreshing {tab_name}...")
        
        # Reset status after 2 seconds
        QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Smart Email Writer",
            "<h2>Smart Email Writer ✨</h2>"
            "<p><b>Version:</b> 1.0.0 (Qt6 Edition)</p>"
            "<p><b>Description:</b> AI-powered email generation and management tool</p>"
            "<p>Built with PyQt6 and powered by Google Gemini AI</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>AI-powered email generation</li>"
            "<li>Bulk email campaigns</li>"
            "<li>Gmail & Outlook support</li>"
            "<li>Excel logging</li>"
            "</ul>"
            "<p><small>© 2024 Smart Email Writer. MIT License.</small></p>"
        )
    
    def show_docs(self):
        """Show documentation info"""
        QMessageBox.information(
            self,
            "Documentation",
            "<h3>Quick Start Guide</h3>"
            "<p><b>1. Setup Profile:</b> Go to Profile tab and fill in your details</p>"
            "<p><b>2. Configure Settings:</b> Set up your SMTP and AI preferences</p>"
            "<p><b>3. Single Email:</b> Generate and send individual emails</p>"
            "<p><b>4. Bulk Email:</b> Upload CSV/Excel for bulk campaigns</p>"
            "<p><b>5. View Logs:</b> Check sent email history</p>"
            "<br>"
            "<p>For more information, check the README.md file in the project directory.</p>"
        )
    
    def set_status(self, message: str, timeout: int = 0):
        """Set status bar message
        
        Args:
            message: Status message to display
            timeout: Timeout in milliseconds (0 for permanent)
        """
        if timeout > 0:
            self.status_bar.showMessage(message, timeout)
        else:
            self.status_label.setText(message)

"""
Settings Tab - Application settings and SMTP configuration
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QComboBox, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt

from services.settings_store import SettingsStore
from config.app_config import GEMINI_MODEL, GROQ_MODEL
import os


class SettingsTab(QWidget):
    """Tab for application settings"""
    
    def __init__(self):
        super().__init__()
        self.settings_store = SettingsStore()
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("⚙️ Application Settings")
        header.setProperty("heading", True)
        layout.addWidget(header)
        
        # SMTP Settings Group
        smtp_group = self.create_smtp_group()
        layout.addWidget(smtp_group)
        
        # AI Settings Group
        ai_group = self.create_ai_group()
        layout.addWidget(ai_group)
        
        # Actions
        actions_layout = self.create_actions_layout()
        layout.addLayout(actions_layout)
        
        layout.addStretch()
    
    def create_smtp_group(self):
        """Create SMTP settings group"""
        group = QGroupBox("📧 SMTP Configuration")
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Gmail", "Outlook"])
        layout.addWidget(self.provider_combo)
        
        layout.addWidget(QLabel("Email Address:"))
        self.smtp_email_input = QLineEdit()
        self.smtp_email_input.setPlaceholderText("your-email@gmail.com")
        layout.addWidget(self.smtp_email_input)
        
        layout.addWidget(QLabel("Password / App Password:"))
        self.smtp_password_input = QLineEdit()
        self.smtp_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.smtp_password_input.setPlaceholderText("Your SMTP password or app-specific password")
        layout.addWidget(self.smtp_password_input)
        
        info = QLabel("ℹ️ For Gmail with 2FA, use an App Password. Settings are saved locally for this session.")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        group.setLayout(layout)
        return group
    
    def create_ai_group(self):
        """Create AI settings group"""
        group = QGroupBox("🤖 AI Configuration")
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("AI Provider:"))
        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItems(["gemini", "groq"])
        self.ai_provider_combo.currentTextChanged.connect(self.on_ai_provider_changed)
        layout.addWidget(self.ai_provider_combo)
        
        layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        layout.addWidget(self.model_combo)
        
        # API Key info
        self.api_key_label = QLabel()
        self.api_key_label.setWordWrap(True)
        layout.addWidget(self.api_key_label)
        
        group.setLayout(layout)
        return group
    
    def create_actions_layout(self):
        """Create actions layout"""
        layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Save Settings")
        self.save_btn.setProperty("primary", True)
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)
        
        self.reload_btn = QPushButton("🔄 Reload Settings")
        self.reload_btn.setProperty("secondary", True)
        self.reload_btn.clicked.connect(self.load_settings)
        layout.addWidget(self.reload_btn)
        
        layout.addStretch()
        
        return layout
    
    def on_ai_provider_changed(self, provider):
        """Handle AI provider change"""
        self.model_combo.clear()
        
        if provider == "gemini":
            self.model_combo.addItems(["gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-1.5-pro"])
            api_key = os.getenv("GEMINI_API_KEY", "")
            status = "✅ Set" if api_key else "❌ Not Set"
            self.api_key_label.setText(f"Gemini API Key: {status} (Set in .env file)")
        else:
            self.model_combo.addItem(GROQ_MODEL)
            api_key = os.getenv("GROQ_API_KEY", "")
            status = "✅ Set" if api_key else "❌ Not Set"
            self.api_key_label.setText(f"Groq API Key: {status} (Set in .env file)")
    
    def load_settings(self):
        """Load settings from store"""
        settings = self.settings_store.load()
        
        # SMTP Settings
        provider = settings.get("smtp_provider", os.getenv("SMTP_PROVIDER", "gmail"))
        self.provider_combo.setCurrentText("Gmail" if provider.lower() == "gmail" else "Outlook")
        
        smtp_email = settings.get("smtp_email", os.getenv("SMTP_EMAIL", ""))
        self.smtp_email_input.setText(smtp_email)
        
        smtp_password = settings.get("smtp_password", os.getenv("SMTP_PASSWORD", ""))
        self.smtp_password_input.setText(smtp_password)
        
        # AI Settings
        ai_provider = settings.get("ai_provider", "gemini")
        self.ai_provider_combo.setCurrentText(ai_provider)
        
        if ai_provider == "gemini":
            model = settings.get("gemini_model", GEMINI_MODEL)
        else:
            model = settings.get("groq_model", GROQ_MODEL)
        
        # Set model after provider is set (which populates the combo)
        index = self.model_combo.findText(model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
    
    def save_settings(self):
        """Save settings to store"""
        settings = {
            "smtp_provider": self.provider_combo.currentText().lower(),
            "smtp_email": self.smtp_email_input.text(),
            "smtp_password": self.smtp_password_input.text(),
            "ai_provider": self.ai_provider_combo.currentText(),
        }
        
        if self.ai_provider_combo.currentText() == "gemini":
            settings["gemini_model"] = self.model_combo.currentText()
        else:
            settings["groq_model"] = self.model_combo.currentText()
        
        try:
            self.settings_store.save(settings)
            QMessageBox.information(self, "Success", "Settings saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{str(e)}")

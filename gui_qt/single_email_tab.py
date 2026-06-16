"""
Single Email Tab - Email composition and sending
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QTextEdit, QComboBox, QPushButton, QCheckBox,
    QFileDialog, QMessageBox, QProgressDialog, QListWidget,
    QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from pathlib import Path

from services.profile_store import ProfileStore
from services.settings_store import SettingsStore
from services.email_sender import EmailSender
from services.excel_logger import ExcelLogger
from clients.gemini_client import GeminiClient
from clients.groq_client import GroqClient
from models.email_models import EmailRequest, Provider, Attachment
from config.app_config import GEMINI_MODEL, GROQ_MODEL


class AIGenerationWorker(QThread):
    """Worker thread for AI email generation"""
    finished = pyqtSignal(str, str)  # subject, body
    error = pyqtSignal(str)
    
    def __init__(self, ai_client, purpose, recipient, tone, language, context, profile, email_length):
        super().__init__()
        self.ai_client = ai_client
        self.purpose = purpose
        self.recipient = recipient
        self.tone = tone
        self.language = language
        self.context = context
        self.profile = profile
        self.email_length = email_length
    
    def run(self):
        try:
            result = self.ai_client.generate_email(
                purpose=self.purpose,
                recipient_name=self.recipient,
                tone=self.tone,
                language=self.language,
                additional_context=self.context,
                profile=self.profile,
                email_length=self.email_length
            )
            self.finished.emit(result.subject, result.body)
        except Exception as e:
            self.error.emit(str(e))


class SingleEmailTab(QWidget):
    """Tab for composing and sending single emails"""
    
    def __init__(self):
        super().__init__()
        self.profile_store = ProfileStore()
        self.settings_store = SettingsStore()
        self.email_sender = EmailSender()
        self.excel_logger = ExcelLogger()
        self.attachments = []
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the user interface"""
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Main widget inside scroll
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("✉️ Single Email Composition")
        header.setProperty("heading", True)
        layout.addWidget(header)
        
        # Email Generation Group
        gen_group = self.create_generation_group()
        layout.addWidget(gen_group)
        
        # Email Content Group
        content_group = self.create_content_group()
        layout.addWidget(content_group)
        
        # Attachment Group
        attachment_group = self.create_attachment_group()
        layout.addWidget(attachment_group)
        
        # Actions
        actions_layout = self.create_actions_layout()
        layout.addLayout(actions_layout)
        
        layout.addStretch()
        
        # Set scroll widget
        scroll.setWidget(scroll_widget)
        
        # Main layout for tab
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def create_generation_group(self):
        """Create email generation settings group"""
        group = QGroupBox("🤖 AI Generation Settings")
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Row 1: Purpose (full width)
        layout.addWidget(QLabel("Purpose/Topic:"))
        self.purpose_input = QLineEdit()
        self.purpose_input.setPlaceholderText("Follow-up meeting request about Q4 roadmap")
        layout.addWidget(self.purpose_input)
        
        # Row 2: Recipient Name and Email (side by side)
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        
        name_layout = QVBoxLayout()
        name_layout.setSpacing(4)
        name_layout.addWidget(QLabel("Recipient Name:"))
        self.recipient_input = QLineEdit()
        self.recipient_input.setPlaceholderText("Jane Doe")
        name_layout.addWidget(self.recipient_input)
        row2.addLayout(name_layout, 1)
        
        email_layout = QVBoxLayout()
        email_layout.setSpacing(4)
        email_layout.addWidget(QLabel("Recipient Email:"))
        self.recipient_email_input = QLineEdit()
        self.recipient_email_input.setPlaceholderText("jane@example.com")
        email_layout.addWidget(self.recipient_email_input)
        row2.addLayout(email_layout, 1)
        
        layout.addLayout(row2)
        
        # Row 3: Tone, Language, Length (3 columns)
        row3 = QHBoxLayout()
        row3.setSpacing(10)
        
        tone_layout = QVBoxLayout()
        tone_layout.setSpacing(4)
        tone_layout.addWidget(QLabel("Tone:"))
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(["Professional", "Friendly", "Concise", "Detailed"])
        tone_layout.addWidget(self.tone_combo)
        row3.addLayout(tone_layout)
        
        lang_layout = QVBoxLayout()
        lang_layout.setSpacing(4)
        lang_layout.addWidget(QLabel("Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Turkish", "German", "French", "Spanish"])
        self.language_combo.setCurrentText("Turkish")
        lang_layout.addWidget(self.language_combo)
        row3.addLayout(lang_layout)
        
        length_layout = QVBoxLayout()
        length_layout.setSpacing(4)
        length_layout.addWidget(QLabel("Length:"))
        self.length_combo = QComboBox()
        self.length_combo.addItems([
            "Very Short",
            "Short",
            "Medium",
            "Long",
            "Ultra Short"
        ])
        self.length_combo.setCurrentIndex(2)
        length_layout.addWidget(self.length_combo)
        row3.addLayout(length_layout)
        
        layout.addLayout(row3)
        
        # Additional Context (compact)
        layout.addWidget(QLabel("Additional Context (optional):"))
        self.context_input = QTextEdit()
        self.context_input.setPlaceholderText("Key points, deadlines, or details...")
        self.context_input.setMaximumHeight(60)
        layout.addWidget(self.context_input)
        
        # Generate Buttons (horizontal)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.generate_btn = QPushButton("🤖 Generate with AI")
        self.generate_btn.setProperty("primary", True)
        self.generate_btn.clicked.connect(self.generate_email)
        btn_layout.addWidget(self.generate_btn)
        
        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.setProperty("secondary", True)
        self.clear_btn.clicked.connect(self.clear_draft)
        btn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(btn_layout)
        
        group.setLayout(layout)
        return group
    
    def create_content_group(self):
        """Create email content editing group"""
        group = QGroupBox("✍️ Email Content")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Subject
        layout.addWidget(QLabel("Subject:"))
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Enter email subject...")
        layout.addWidget(self.subject_input)
        
        # Body
        layout.addWidget(QLabel("Body:"))
        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText("Enter email body or generate with AI...")
        self.body_input.setMinimumHeight(200)
        layout.addWidget(self.body_input)
        
        group.setLayout(layout)
        return group
    
    def create_attachment_group(self):
        """Create attachment management group"""
        group = QGroupBox("📎 Attachments (Optional)")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.add_attachment_btn = QPushButton("➕ Add Files")
        self.add_attachment_btn.clicked.connect(self.add_attachments)
        btn_layout.addWidget(self.add_attachment_btn)
        
        self.remove_attachment_btn = QPushButton("➖ Remove")
        self.remove_attachment_btn.clicked.connect(self.remove_attachment)
        btn_layout.addWidget(self.remove_attachment_btn)
        
        layout.addLayout(btn_layout)
        
        self.attachment_list = QListWidget()
        self.attachment_list.setMaximumHeight(60)
        layout.addWidget(self.attachment_list)
        
        group.setLayout(layout)
        return group
    
    def create_actions_layout(self):
        """Create actions layout with send button"""
        layout = QHBoxLayout()
        
        self.log_checkbox = QCheckBox("Log to Excel after send")
        self.log_checkbox.setChecked(True)
        layout.addWidget(self.log_checkbox)
        
        layout.addStretch()
        
        self.send_btn = QPushButton("📤 Send Email")
        self.send_btn.setProperty("primary", True)
        self.send_btn.setMinimumWidth(200)
        self.send_btn.clicked.connect(self.send_email)
        layout.addWidget(self.send_btn)
        
        return layout
    
    def load_settings(self):
        """Load saved settings"""
        settings = self.settings_store.load()
        if "default_purpose" in settings:
            self.purpose_input.setText(settings["default_purpose"])
    
    def generate_email(self):
        """Generate email using AI"""
        purpose = self.purpose_input.text().strip()
        if not purpose:
            QMessageBox.warning(self, "Missing Information", "Please enter a purpose/topic for the email.")
            return
        
        # Get AI client from settings
        settings = self.settings_store.load()
        ai_provider = settings.get("ai_provider", "gemini")
        
        try:
            if ai_provider == "groq":
                model = settings.get("groq_model", GROQ_MODEL)
                api_key = os.getenv("GROQ_API_KEY", "")
                if not api_key:
                    QMessageBox.warning(self, "Missing API Key", "GROQ_API_KEY not found in environment.")
                    return
                ai_client = GroqClient(api_key=api_key, model_name=model)
            else:
                model = settings.get("gemini_model", GEMINI_MODEL)
                api_key = os.getenv("GEMINI_API_KEY", "")
                if not api_key:
                    QMessageBox.warning(self, "Missing API Key", "GEMINI_API_KEY not found in environment.")
                    return
                ai_client = GeminiClient(api_key=api_key, model_name=model)
            
            # Show progress
            progress = QProgressDialog("Generating email with AI...", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setWindowTitle("AI Generation")
            progress.show()
            
            # Create worker thread
            self.worker = AIGenerationWorker(
                ai_client=ai_client,
                purpose=purpose,
                recipient=self.recipient_input.text(),
                tone=self.tone_combo.currentText(),
                language=self.language_combo.currentText(),
                context=self.context_input.toPlainText(),
                profile=self.profile_store.load(),
                email_length=self.length_combo.currentText()
            )
            
            self.worker.finished.connect(lambda subj, body: self.on_generation_finished(subj, body, progress))
            self.worker.error.connect(lambda err: self.on_generation_error(err, progress))
            self.worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize AI client: {str(e)}")
    
    def on_generation_finished(self, subject, body, progress):
        """Handle AI generation completion"""
        progress.close()
        self.subject_input.setText(subject)
        self.body_input.setPlainText(body)
        QMessageBox.information(self, "Success", "Email generated successfully!")
    
    def on_generation_error(self, error, progress):
        """Handle AI generation error"""
        progress.close()
        QMessageBox.critical(self, "Generation Error", f"Failed to generate email:\n{error}")
    
    def clear_draft(self):
        """Clear the email draft"""
        self.subject_input.clear()
        self.body_input.clear()
    
    def add_attachments(self):
        """Add file attachments"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files to Attach",
            "",
            "All Files (*.*)"
        )
        
        for file_path in files:
            file_name = Path(file_path).name
            if file_name not in [self.attachment_list.item(i).text() for i in range(self.attachment_list.count())]:
                self.attachment_list.addItem(file_name)
                self.attachments.append(file_path)
    
    def remove_attachment(self):
        """Remove selected attachment"""
        current_row = self.attachment_list.currentRow()
        if current_row >= 0:
            self.attachment_list.takeItem(current_row)
            self.attachments.pop(current_row)
    
    def send_email(self):
        """Send the email"""
        # Validation
        if not self.subject_input.text().strip():
            QMessageBox.warning(self, "Missing Subject", "Please enter an email subject.")
            return
        
        if not self.body_input.toPlainText().strip():
            QMessageBox.warning(self, "Missing Body", "Please enter email body.")
            return
        
        if not self.recipient_email_input.text().strip():
            QMessageBox.warning(self, "Missing Recipient", "Please enter recipient email address.")
            return
        
        # Get SMTP settings from settings tab (we'll implement this later)
        # For now, use environment variables
        settings = self.settings_store.load()
        provider_str = settings.get("smtp_provider", os.getenv("SMTP_PROVIDER", "gmail")).lower()
        provider = Provider.GMAIL if provider_str == "gmail" else Provider.OUTLOOK
        
        sender_email = settings.get("smtp_email", os.getenv("SMTP_EMAIL", ""))
        sender_password = settings.get("smtp_password", os.getenv("SMTP_PASSWORD", ""))
        
        if not sender_email or not sender_password:
            QMessageBox.warning(
                self,
                "SMTP Not Configured",
                "Please configure SMTP settings in the Settings tab first."
            )
            return
        
        # Prepare attachments
        attachment_objects = []
        for file_path in self.attachments:
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                file_name = Path(file_path).name
                attachment_objects.append(
                    Attachment(filename=file_name, content=content, mime_type="application/octet-stream")
                )
            except Exception as e:
                QMessageBox.warning(self, "Attachment Error", f"Failed to read {file_name}: {str(e)}")
                return
        
        # Create email request
        request = EmailRequest(
            provider=provider,
            sender_email=sender_email,
            sender_password=sender_password,
            recipient_email=self.recipient_email_input.text(),
            subject=self.subject_input.text(),
            body=self.body_input.toPlainText(),
            attachments=attachment_objects if attachment_objects else None
        )
        
        # Show progress
        progress = QProgressDialog("Sending email...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle("Sending")
        progress.show()
        
        try:
            success, error_message = self.email_sender.send(request)
            progress.close()
            
            if success:
                QMessageBox.information(self, "Success", "Email sent successfully!")
                
                # Log to Excel if enabled
                if self.log_checkbox.isChecked():
                    try:
                        self.excel_logger.append(
                            sender_email=sender_email,
                            recipient_email=request.recipient_email,
                            subject=request.subject,
                            body=request.body,
                            provider=provider.name
                        )
                    except Exception as log_error:
                        QMessageBox.warning(self, "Logging Error", f"Email sent but logging failed: {str(log_error)}")
                
                # Clear form
                self.clear_draft()
                self.recipient_input.clear()
                self.recipient_email_input.clear()
                self.attachment_list.clear()
                self.attachments = []
            else:
                QMessageBox.critical(self, "Send Failed", f"Failed to send email:\n{error_message}")
        
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", f"An error occurred:\n{str(e)}")

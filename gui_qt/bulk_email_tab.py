"""
Bulk Email Tab - Bulk email campaigns
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QTextEdit, QComboBox, QPushButton, QCheckBox,
    QFileDialog, QMessageBox, QProgressDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import pandas as pd
from pathlib import Path

from services.file_parser import FileParser
from services.bulk_email_sender import BulkEmailSender
from services.profile_store import ProfileStore
from services.settings_store import SettingsStore
from clients.gemini_client import GeminiClient
from clients.groq_client import GroqClient
from models.email_models import BulkEmailRequest, Provider
from config.app_config import GEMINI_MODEL, GROQ_MODEL
import os


class BulkEmailTab(QWidget):
    """Tab for bulk email campaigns"""
    
    def __init__(self):
        super().__init__()
        self.file_parser = FileParser()
        self.profile_store = ProfileStore()
        self.settings_store = SettingsStore()
        self.recipients = []
        self.file_columns = []
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("📧 Bulk Email Campaign")
        header.setProperty("heading", True)
        layout.addWidget(header)
        
        # File Upload Group
        upload_group = self.create_upload_group()
        layout.addWidget(upload_group)
        
        # Data Preview (initially hidden)
        self.preview_group = QGroupBox("📊 Data Preview")
        self.preview_layout = QVBoxLayout()
        self.preview_table = QTableWidget()
        self.preview_table.setMaximumHeight(200)
        self.preview_layout.addWidget(self.preview_table)
        self.preview_group.setLayout(self.preview_layout)
        self.preview_group.setVisible(False)
        layout.addWidget(self.preview_group)
        
        # Email Composition Group (initially hidden)
        self.composition_group = self.create_composition_group()
        self.composition_group.setVisible(False)
        layout.addWidget(self.composition_group)
        
        # Actions
        self.actions_layout = self.create_actions_layout()
        layout.addLayout(self.actions_layout)
    
    def create_upload_group(self):
        """Create file upload group"""
        group = QGroupBox("📁 Upload Recipient List")
        layout = QVBoxLayout()
        
        info_label = QLabel("Upload a CSV or Excel file containing recipient information (Name, Email, Description)")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        btn_layout = QHBoxLayout()
        self.upload_btn = QPushButton("📂 Select File")
        self.upload_btn.setProperty("primary", True)
        self.upload_btn.clicked.connect(self.upload_file)
        btn_layout.addWidget(self.upload_btn)
        
        self.file_label = QLabel("No file selected")
        btn_layout.addWidget(self.file_label)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        group.setLayout(layout)
        return group
    
    def create_composition_group(self):
        """Create email composition group"""
        group = QGroupBox("✍️ Email Composition")
        layout = QVBoxLayout()
        
        # AI vs Template toggle
        toggle_layout = QHBoxLayout()
        self.use_ai_checkbox = QCheckBox("🤖 Use AI Generation (personalized for each recipient)")
        self.use_ai_checkbox.stateChanged.connect(self.toggle_composition_mode)
        toggle_layout.addWidget(self.use_ai_checkbox)
        layout.addLayout(toggle_layout)
        
        # Template-based fields
        self.template_widget = QWidget()
        template_layout = QVBoxLayout()
        template_layout.addWidget(QLabel("Subject Template:"))
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Use {name}, {email}, {description} for personalization")
        template_layout.addWidget(self.subject_input)
        
        template_layout.addWidget(QLabel("Body Template:"))
        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText("Dear {name},\n\nI hope this email finds you well...")
        self.body_input.setMaximumHeight(150)
        template_layout.addWidget(self.body_input)
        self.template_widget.setLayout(template_layout)
        layout.addWidget(self.template_widget)
        
        # AI-based fields (initially hidden)
        self.ai_widget = QWidget()
        ai_layout = QVBoxLayout()
        ai_layout.addWidget(QLabel("AI Purpose:"))
        self.ai_purpose_input = QLineEdit()
        self.ai_purpose_input.setPlaceholderText("Product introduction, Meeting request, etc.")
        ai_layout.addWidget(self.ai_purpose_input)
        self.ai_widget.setLayout(ai_layout)
        self.ai_widget.setVisible(False)
        layout.addWidget(self.ai_widget)
        
        # Settings
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Delay (seconds):"))
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0, 10)
        self.delay_spin.setValue(1.0)
        self.delay_spin.setSingleStep(0.1)
        settings_layout.addWidget(self.delay_spin)
        
        self.log_checkbox = QCheckBox("Log to Excel")
        self.log_checkbox.setChecked(True)
        settings_layout.addWidget(self.log_checkbox)
        settings_layout.addStretch()
        
        layout.addLayout(settings_layout)
        
        group.setLayout(layout)
        return group
    
    def create_actions_layout(self):
        """Create actions layout"""
        layout = QHBoxLayout()
        layout.addStretch()
        
        self.send_bulk_btn = QPushButton("🚀 Send Bulk Emails")
        self.send_bulk_btn.setProperty("primary", True)
        self.send_bulk_btn.setMinimumWidth(200)
        self.send_bulk_btn.setEnabled(False)
        self.send_bulk_btn.clicked.connect(self.send_bulk_emails)
        layout.addWidget(self.send_bulk_btn)
        
        return layout
    
    def upload_file(self):
        """Upload and parse CSV/Excel file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Recipient List",
            "",
            "CSV Files (*.csv);;Excel Files (*.xlsx *.xls)"
        )
        
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                file_name = Path(file_path).name
                self.file_label.setText(f"✅ {file_name}")
                
                # Get columns
                self.file_columns = self.file_parser.get_file_columns(file_content, file_name)
                
                # For simplicity, assume first 3 columns are name, email, description
                if len(self.file_columns) >= 3:
                    name_col, email_col, desc_col = self.file_columns[0], self.file_columns[1], self.file_columns[2]
                    
                    # Parse recipients
                    self.recipients = self.file_parser.parse_file(
                        file_content, file_name, name_col, email_col, desc_col
                    )
                    
                    # Show preview
                    self.show_preview(file_content, file_name, name_col, email_col, desc_col)
                    
                    # Enable composition
                    self.composition_group.setVisible(True)
                    self.send_bulk_btn.setEnabled(True)
                    
                    QMessageBox.information(
                        self,
                        "File Loaded",
                        f"Successfully loaded {len(self.recipients)} recipients!"
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Invalid File",
                        "File must have at least 3 columns (Name, Email, Description)"
                    )
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")
    
    def show_preview(self, file_content, file_name, name_col, email_col, desc_col):
        """Show data preview"""
        try:
            preview_data, total_rows = self.file_parser.preview_data(
                file_content, file_name, name_col, email_col, desc_col
            )
            
            self.preview_table.setRowCount(len(preview_data))
            self.preview_table.setColumnCount(len(preview_data.columns))
            self.preview_table.setHorizontalHeaderLabels(preview_data.columns.tolist())
            
            for i, row in preview_data.iterrows():
                for j, value in enumerate(row):
                    self.preview_table.setItem(i, j, QTableWidgetItem(str(value)))
            
            self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.preview_group.setVisible(True)
        
        except Exception as e:
            print(f"Preview error: {e}")
    
    def toggle_composition_mode(self, state):
        """Toggle between AI and template mode"""
        use_ai = state == Qt.CheckState.Checked.value
        self.template_widget.setVisible(not use_ai)
        self.ai_widget.setVisible(use_ai)
    
    def send_bulk_emails(self):
        """Send bulk emails"""
        if not self.recipients:
            QMessageBox.warning(self, "No Recipients", "Please upload a recipient list first.")
            return
        
        use_ai = self.use_ai_checkbox.isChecked()
        
        # Validation
        if not use_ai:
            if not self.subject_input.text().strip() or not self.body_input.toPlainText().strip():
                QMessageBox.warning(self, "Missing Content", "Please enter subject and body templates.")
                return
        else:
            if not self.ai_purpose_input.text().strip():
                QMessageBox.warning(self, "Missing Purpose", "Please enter AI purpose.")
                return
        
        # Get settings
        settings = self.settings_store.load()
        provider_str = settings.get("smtp_provider", os.getenv("SMTP_PROVIDER", "gmail")).lower()
        provider = Provider.GMAIL if provider_str == "gmail" else Provider.OUTLOOK
        
        sender_email = settings.get("smtp_email", os.getenv("SMTP_EMAIL", ""))
        sender_password = settings.get("smtp_password", os.getenv("SMTP_PASSWORD", ""))
        
        if not sender_email or not sender_password:
            QMessageBox.warning(self, "SMTP Not Configured", "Please configure SMTP in Settings tab.")
            return
        
        # Create bulk request
        request = BulkEmailRequest(
            provider=provider,
            sender_email=sender_email,
            sender_password=sender_password,
            subject=self.subject_input.text() if not use_ai else "AI Generated",
            body_template=self.body_input.toPlainText() if not use_ai else "AI Generated",
            recipients=self.recipients,
            use_ai_generation=use_ai,
            ai_purpose=self.ai_purpose_input.text() if use_ai else "",
            ai_tone="Professional",
            ai_language="Turkish",
            ai_length="Medium (3-4 paragraphs)"
        )
        
        # Initialize AI client if needed
        ai_client = None
        if use_ai:
            ai_provider = settings.get("ai_provider", "gemini")
            try:
                if ai_provider == "groq":
                    model = settings.get("groq_model", GROQ_MODEL)
                    api_key = os.getenv("GROQ_API_KEY", "")
                    ai_client = GroqClient(api_key=api_key, model_name=model)
                else:
                    model = settings.get("gemini_model", GEMINI_MODEL)
                    api_key = os.getenv("GEMINI_API_KEY", "")
                    ai_client = GeminiClient(api_key=api_key, model_name=model)
            except Exception as e:
                QMessageBox.critical(self, "AI Error", f"Failed to initialize AI: {str(e)}")
                return
        
        # Send emails with progress dialog
        bulk_sender = BulkEmailSender(ai_client=ai_client)
        
        progress = QProgressDialog("Sending bulk emails...", "Cancel", 0, len(self.recipients), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setWindowTitle("Bulk Send Progress")
        
        def progress_callback(current, total, name, success, method="Template"):
            progress.setValue(current)
            status = "✅" if success else "❌"
            progress.setLabelText(f"{status} [{method}] {name} ({current}/{total})")
        
        try:
            results = bulk_sender.send_bulk_emails(
                request,
                delay_seconds=self.delay_spin.value(),
                log_to_excel=self.log_checkbox.isChecked(),
                progress_callback=progress_callback,
                profile=self.profile_store.load()
            )
            
            progress.close()
            
            # Show results
            QMessageBox.information(
                self,
                "Bulk Send Complete",
                f"✅ Successful: {results['successful_sends']}\n"
                f"❌ Failed: {results['failed_sends']}\n"
                f"📊 Total: {results['total_recipients']}"
            )
        
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", f"Bulk send failed:\n{str(e)}")

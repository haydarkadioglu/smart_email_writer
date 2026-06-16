"""
Logs Tab - View sent email history
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt
import pandas as pd
from pathlib import Path


class LogsTab(QWidget):
    """Tab for viewing email logs"""
    
    def __init__(self):
        super().__init__()
        self.log_file = Path("logs/sent_emails.xlsx")
        self.init_ui()
        self.load_logs()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("📊 Email Logs")
        header.setProperty("heading", True)
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.load_logs)
        header_layout.addWidget(self.refresh_btn)
        
        self.export_btn = QPushButton("💾 Export")
        self.export_btn.clicked.connect(self.export_logs)
        header_layout.addWidget(self.export_btn)
        
        layout.addLayout(header_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        
        # Status
        self.status_label = QLabel("No logs loaded")
        layout.addWidget(self.status_label)
    
    def load_logs(self):
        """Load logs from Excel file"""
        if not self.log_file.exists():
            self.status_label.setText("No log file found. Logs will be created when you send emails.")
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return
        
        try:
            df = pd.read_excel(self.log_file)
            
            if df.empty:
                self.status_label.setText("Log file is empty")
                self.table.setRowCount(0)
                self.table.setColumnCount(0)
                return
            
            # Setup table
            self.table.setRowCount(len(df))
            self.table.setColumnCount(len(df.columns))
            self.table.setHorizontalHeaderLabels(df.columns.tolist())
            
            # Populate table
            for i, row in df.iterrows():
                for j, value in enumerate(row):
                    item = QTableWidgetItem(str(value))
                    self.table.setItem(i, j, item)
            
            # Resize columns
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            self.table.horizontalHeader().setStretchLastSection(True)
            
            self.status_label.setText(f"Loaded {len(df)} email log(s)")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load logs:\n{str(e)}")
            self.status_label.setText("Failed to load logs")
    
    def export_logs(self):
        """Export logs to a new file"""
        if not self.log_file.exists():
            QMessageBox.warning(self, "No Logs", "No logs available to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            "email_logs_export.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                df = pd.read_excel(self.log_file)
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "Success", f"Logs exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export logs:\n{str(e)}")

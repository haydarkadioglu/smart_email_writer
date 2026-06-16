"""
Profile Tab - User profile management
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QTextEdit, QPushButton, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt

from services.profile_store import ProfileStore


class ProfileTab(QWidget):
    """Tab for managing user profile"""
    
    def __init__(self):
        super().__init__()
        self.profile_store = ProfileStore()
        self.init_ui()
        self.load_profile()
    
    def init_ui(self):
        """Initialize the user interface"""
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Main widget
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("👤 User Profile")
        header.setProperty("heading", True)
        layout.addWidget(header)
        
        info = QLabel("This information is used when generating AI emails")
        layout.addWidget(info)
        
        # Personal Info Group
        personal_group = self.create_personal_group()
        layout.addWidget(personal_group)
        
        # Professional Info Group
        prof_group = self.create_professional_group()
        layout.addWidget(prof_group)
        
        # Actions
        actions_layout = self.create_actions_layout()
        layout.addLayout(actions_layout)
        
        layout.addStretch()
        
        # Set scroll area
        scroll.setWidget(main_widget)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def create_personal_group(self):
        """Create personal information group"""
        group = QGroupBox("Personal Information")
        layout = QVBoxLayout()
        
        # Row 1
        row1 = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit()
        col1.addWidget(self.name_input)
        row1.addLayout(col1)
        
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("Email:"))
        self.email_input = QLineEdit()
        col2.addWidget(self.email_input)
        row1.addLayout(col2)
        layout.addLayout(row1)
        
        # Row 2
        row2 = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("Phone:"))
        self.phone_input = QLineEdit()
        col1.addWidget(self.phone_input)
        row2.addLayout(col1)
        
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("Location:"))
        self.location_input = QLineEdit()
        col2.addWidget(self.location_input)
        row2.addLayout(col2)
        layout.addLayout(row2)
        
        group.setLayout(layout)
        return group
    
    def create_professional_group(self):
        """Create professional information group"""
        group = QGroupBox("Professional Information")
        layout = QVBoxLayout()
        
        # Row 1
        row1 = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("Title/Position:"))
        self.title_input = QLineEdit()
        col1.addWidget(self.title_input)
        row1.addLayout(col1)
        
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("Company:"))
        self.company_input = QLineEdit()
        col2.addWidget(self.company_input)
        row1.addLayout(col2)
        layout.addLayout(row1)
        
        # Row 2
        row2 = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("Experience (years):"))
        self.experience_input = QLineEdit()
        col1.addWidget(self.experience_input)
        row2.addLayout(col1)
        
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("Website/Portfolio:"))
        self.website_input = QLineEdit()
        col2.addWidget(self.website_input)
        row2.addLayout(col2)
        layout.addLayout(row2)
        
        # Row 3
        row3 = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("LinkedIn:"))
        self.linkedin_input = QLineEdit()
        col1.addWidget(self.linkedin_input)
        row3.addLayout(col1)
        
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("GitHub:"))
        self.github_input = QLineEdit()
        col2.addWidget(self.github_input)
        row3.addLayout(col2)
        layout.addLayout(row3)
        
        # Skills
        layout.addWidget(QLabel("Skills (comma-separated):"))
        self.skills_input = QTextEdit()
        self.skills_input.setMaximumHeight(80)
        layout.addWidget(self.skills_input)
        
        # Summary
        layout.addWidget(QLabel("Professional Summary:"))
        self.summary_input = QTextEdit()
        self.summary_input.setMaximumHeight(100)
        layout.addWidget(self.summary_input)
        
        # Achievements
        layout.addWidget(QLabel("Key Achievements:"))
        self.achievements_input = QTextEdit()
        self.achievements_input.setMaximumHeight(80)
        layout.addWidget(self.achievements_input)
        
        group.setLayout(layout)
        return group
    
    def create_actions_layout(self):
        """Create actions layout"""
        layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Save Profile")
        self.save_btn.setProperty("primary", True)
        self.save_btn.clicked.connect(self.save_profile)
        layout.addWidget(self.save_btn)
        
        self.reload_btn = QPushButton("🔄 Reload Profile")
        self.reload_btn.setProperty("secondary", True)
        self.reload_btn.clicked.connect(self.load_profile)
        layout.addWidget(self.reload_btn)
        
        layout.addStretch()
        
        return layout
    
    def load_profile(self):
        """Load profile from store"""
        profile = self.profile_store.load()
        self.name_input.setText(profile.get("name", ""))
        self.title_input.setText(profile.get("title", ""))
        self.company_input.setText(profile.get("company", ""))
        self.experience_input.setText(profile.get("experience", ""))
        self.location_input.setText(profile.get("location", ""))
        self.phone_input.setText(profile.get("phone", ""))
        self.email_input.setText(profile.get("email", ""))
        self.website_input.setText(profile.get("website", ""))
        self.linkedin_input.setText(profile.get("linkedin", ""))
        self.github_input.setText(profile.get("github", ""))
        self.skills_input.setPlainText(profile.get("skills", ""))
        self.summary_input.setPlainText(profile.get("summary", ""))
        self.achievements_input.setPlainText(profile.get("achievements", ""))
    
    def save_profile(self):
        """Save profile to store"""
        profile = {
            "name": self.name_input.text(),
            "title": self.title_input.text(),
            "company": self.company_input.text(),
            "experience": self.experience_input.text(),
            "location": self.location_input.text(),
            "phone": self.phone_input.text(),
            "email": self.email_input.text(),
            "website": self.website_input.text(),
            "linkedin": self.linkedin_input.text(),
            "github": self.github_input.text(),
            "skills": self.skills_input.toPlainText(),
            "summary": self.summary_input.toPlainText(),
            "achievements": self.achievements_input.toPlainText()
        }
        
        try:
            self.profile_store.save(profile)
            QMessageBox.information(self, "Success", "Profile saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save profile:\n{str(e)}")

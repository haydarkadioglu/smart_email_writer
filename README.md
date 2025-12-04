# 📧 Smart Email Writer

> **AI-Powered Email Generation & Management Tool**

A comprehensive Streamlit application that leverages Google's Gemini AI to generate professional emails, supports multiple email providers, and maintains detailed logs of all communications.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.38.0-red.svg)
![Gemini](https://img.shields.io/badge/Gemini-2.0--flash--lite-green.svg)

## ✨ Features

Smart Email Writer leverages **Gemini 2.0 Flash Lite** AI to generate professional emails with customizable tone, length, and language options. The app features comprehensive profile management for personal and professional details, supports Gmail and Outlook/Hotmail delivery with file attachments, and maintains detailed Excel logs of all sent emails. 

### 🆕 **NEW: Bulk Email Feature**
- **CSV/Excel Import**: Upload recipient lists from CSV or Excel files
- **Dynamic Column Mapping**: Map any column names to recipient data fields
- **Custom Fields**: Add personalized fields for advanced personalization
- **🤖 AI-Powered Generation**: Generate unique emails for each recipient using Gemini/Groq
- **📝 Template-based Personalization**: Use placeholders for quick personalization
- **Email Validation**: Automatic validation of email addresses
- **Progress Tracking**: Real-time progress bar and status updates
- **Rate Limiting**: Configurable delays to avoid spam filters
- **Batch Processing**: Send hundreds of personalized emails efficiently

Perfect for job applications, business communications, marketing campaigns, and automated email workflows.

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Gemini API Key** ([Get one here](https://aistudio.google.com/api-keys))
- **Email credentials** (Gmail App Password recommended for 2FA accounts)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/haydarkadioglu/smart_email_writer
   cd smart_email_writer
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   
   Create `.env` file in the root directory:
   ```bash
   # Required
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # Optional (for auto-filling SMTP settings)
   SMTP_PROVIDER=gmail
   SMTP_EMAIL=your-email@gmail.com
   SMTP_PASSWORD=your_app_password
   ```

5. **Run the application**
   ```bash
   streamlit run main.py
   ```

## 🔧 Configuration

### Gmail Setup (2FA Enabled)
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification**
3. Generate **App Password**:
   - Security → 2-Step Verification → App passwords
   - Select "Mail" and "Other (Custom name)"
   - Use the 16-character password in your `.env` file

### Outlook/Hotmail Setup
- Use your regular email password
- For enhanced security, consider using App Passwords if available

## 📁 Project Structure

```
smart_email_writer/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── config/
│   ├── app_config.py      # Application settings
│   └── profile.json       # User profile storage
├── clients/
│   ├── gemini_client.py   # AI email generation
│   ├── gmail_client.py    # Gmail SMTP client
│   ├── outlook_client.py  # Outlook SMTP client
│   └── smtp_base.py       # Base SMTP functionality
├── services/
│   ├── email_sender.py    # Email orchestration
│   ├── excel_logger.py    # Activity logging
│   ├── profile_store.py   # Profile management
│   ├── file_parser.py     # CSV/Excel file parsing
│   └── bulk_email_sender.py # Bulk email processing
├── models/
│   └── email_models.py    # Data models
├── ui/
│   └── app.py            # Streamlit interface
└── logs/
    └── sent_emails.xlsx  # Email activity log
```

## 🎯 Usage Examples

### Single Email Generation
**Job Application Email**
1. **Fill your profile** with professional details
2. **Set purpose**: "Software Developer position application"
3. **Add context**: Job requirements, company details
4. **Select tone**: Professional, Length: Medium
5. **Generate & send**

**Business Follow-up**
1. **Purpose**: "Meeting follow-up regarding Q4 project"
2. **Context**: Meeting outcomes, next steps
3. **Tone**: Professional, Length: Short
4. **Generate & send**

### 📧 Bulk Email Campaigns

**🤖 AI-Powered Marketing Campaign**
1. **Prepare CSV/Excel file** with columns: Name, Email, Company, Industry, Description
2. **Upload file** and map columns to recipient fields
3. **Enable AI Generation** and set purpose: "Introduce our new product to potential clients"
4. **Configure AI settings**: Professional tone, English, Medium length
5. **Add context**: "We're launching a new AI-powered CRM solution"
6. **Preview data** and **Send bulk emails** - AI generates unique emails for each recipient

**📝 Template-based Event Invitations**
1. **Create recipient list** with Name, Email, Event, Date, Location
2. **Map columns** and add custom fields for event details
3. **Use template**: "Dear {name}, you're invited to {event} on {date} at {location}"
4. **Send personalized invitations** to all recipients

**🎯 Hybrid Approach**
- Use **AI Generation** for high-value, personalized communications
- Use **Template-based** for quick, standardized messages
- Mix both approaches based on your campaign needs

## 🔒 Security & Privacy

- **No credential storage**: SMTP passwords are session-only
- **Local data**: All profiles and logs stored locally
- **Secure transmission**: SMTP with TLS encryption
- **API key protection**: Store in environment variables only

## 🛠️ Troubleshooting

### Common Issues

**"Application-specific password required"**
- Enable 2FA and create App Password for Gmail
- Use App Password instead of regular password

**"Failed to generate email"**
- Check GEMINI_API_KEY is set correctly
- Verify internet connection
- Try different model (Pro vs Flash)

**"SMTP authentication failed"**
- Verify email/password combination
- Check if 2FA requires App Password
- Ensure SMTP settings are correct

## 📈 Future Enhancements

- [x] ~~Bulk email sending~~ ✅ **COMPLETED**
- [ ] Email templates library
- [ ] Email scheduling
- [ ] Advanced analytics
- [ ] Multi-account support
- [ ] Email signature management
- [ ] Email campaign analytics
- [ ] A/B testing for email templates

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.



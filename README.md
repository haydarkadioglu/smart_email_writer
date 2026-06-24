# 📧 SEW AI

> **AI-Powered Email Generation**

A modern desktop application that uses AI (Gemini, Groq, OpenAI, Claude, DeepSeek, OpenRouter) to generate and send professional emails — individually or in bulk.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![pywebview](https://img.shields.io/badge/pywebview-4.x-orange.svg)
![Gemini](https://img.shields.io/badge/Gemini-2.0--flash-green.svg)

## ✨ Features

- **AI Email Generation** — Powered by Gemini, Groq, OpenAI, Claude, DeepSeek or OpenRouter
- **Single Email Composer** — Recipient info, prompt templates, AI refine, undo/redo history, tone analysis
- **Bulk Email Campaigns** — CSV/Excel upload with smart column mapping, per-recipient AI generation, approval workflow
- **Email Templates** — Save and reuse email draft templates and AI prompt templates
- **SMTP Debug Console** — Real-time SMTP step logging per send
- **AI Tone Analysis** — Formality, Friendliness, Urgency, Clarity scores + AI advice
- **Cost & Token Tracker** — Estimates token usage and cost per AI call with session log
- **Multiple Themes** — Obsidian Dark, Cyberpunk Glass, Emerald Forest, Sunset Glow, Classic Slate
- **Send History** — Full log of generated and sent emails
- **Attachments** — Attach files to single emails
- **AI Fallback Chain** — Set a priority list of providers; if one fails or hits rate limits, SmartMail seamlessly falls back to the next.
- **Custom Frameless UI** — Native, fully themed custom title bar matching the app's aesthetic.
- **Chat Assistant** — AI chat interface to brainstorm drafts, analyze emails, and automatically save chats to drafts.
- **CV to Profile** — Auto-extract user profile details (Name, Role, Company) directly from uploaded PDF or Word CVs.
- **Standalone EXE** — Build a single `.exe` with PyInstaller

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- An API key for at least one AI provider (e.g. [Gemini](https://aistudio.google.com/api-keys))
- Gmail/Outlook credentials for sending

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

   Create a `.env.local` file in the root directory:
   ```env
   # AI Provider Keys (add whichever you have)
   GEMINI_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   CLAUDE_API_KEY=your_claude_api_key_here
   DEEPSEEK_API_KEY=your_deepseek_api_key_here
   OPENROUTER_API_KEY=your_openrouter_api_key_here

   # Optional: pre-fill SMTP settings
   SMTP_PROVIDER=gmail
   SMTP_EMAIL=your-email@gmail.com
   ```

5. **Run the application**
   ```bash
   python main.py
   # or
   run_app.bat
   ```

6. **Build standalone EXE** (optional)
   ```bash
   python build.py
   # Output: dist/SmartEmailWriter.exe
   ```

## 🔧 Configuration

### Gmail Setup (2FA Enabled)
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification**
3. Generate **App Password**:
   - Security → 2-Step Verification → App passwords
   - Select "Mail" and "Other (Custom name)"
   - Use the 16-character password in the Settings tab

### Outlook/Hotmail Setup
- Use your regular email password
- For enhanced security, use App Passwords if available

## 📁 Project Structure

```
smart_email_writer/
├── main.py                    # Application entry point (pywebview)
├── build.py                   # PyInstaller build script
├── run_app.bat                # Windows launch script
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
├── config/
│   ├── app_config.py          # Application settings
│   ├── profile.json           # User profile storage
│   └── usage_logs.json        # AI token usage log
├── clients/
│   ├── gemini_client.py       # Google Gemini AI client
│   ├── groq_client.py         # Groq AI client
│   ├── openai_compat_base.py  # OpenAI-compatible base
│   ├── openai_client.py       # OpenAI client
│   ├── claude_client.py       # Anthropic Claude client
│   ├── deepseek_client.py     # DeepSeek client
│   ├── openrouter_client.py   # OpenRouter client
│   ├── gmail_client.py        # Gmail SMTP client
│   ├── outlook_client.py      # Outlook SMTP client
│   └── smtp_base.py           # Base SMTP functionality
├── services/
│   ├── email_sender.py        # Email orchestration
│   ├── excel_logger.py        # Activity logging
│   ├── profile_store.py       # Profile management
│   ├── file_parser.py         # CSV/Excel parsing
│   └── bulk_email_sender.py   # Bulk email processing
├── models/
│   └── email_models.py        # Data models
├── ui_webview/
│   ├── api.py                 # pywebview API class
│   ├── mixins/                # Feature mixins (email, config, bulk…)
│   └── templates/             # HTML/CSS/JS frontend
│       ├── index.html
│       ├── style.css
│       ├── css/               # Modular stylesheets
│       └── js/                # Tab logic modules
└── logs/
    └── sent_emails.xlsx       # Email activity log
```

## 🎯 Usage Examples

### Single Email
1. Go to **Single Email** tab
2. Fill in Recipient name, email, company
3. Choose a **Prompt Template** or type a custom purpose
4. Select your AI provider and click **✦ Generate Email**
5. Optionally click **Refine** or **🎭 Analyze Tone**
6. Click **📨 Send Email** — watch the SMTP console for real-time progress

### Bulk Email Campaign
1. Go to **Bulk Email** tab
2. Upload a CSV/Excel file with recipient data
3. Use the **Column Mapping** panel to map Name, Email, Company columns
4. Set a common purpose (or use per-recipient purpose column)
5. Click **✦ Generate All** → review emails in the Approval workflow
6. Click **📨 Send All** — monitor progress in the SMTP Console

### Templates
- Go to **Templates** to manage saved email templates and AI prompt templates
- Prompt templates appear in the dropdown on the Single Email tab

### Cost Tracking
- Go to **Settings** → **View Stats →** to see token usage and estimated costs per AI call

## 🔒 Security & Privacy

- **No credential storage in code**: SMTP passwords stored only in Settings (local config)
- **Local data**: All profiles, logs and usage data stored locally
- **Secure transmission**: SMTP with TLS encryption
- **API key protection**: Stored in environment variables only

## 🛠️ Troubleshooting

**"Application-specific password required"**
- Enable 2FA and create App Password for Gmail
- Use App Password instead of regular password

**"Failed to generate email"**
- Check that your API key is set in `.env.local`
- Verify internet connection
- Try a different AI provider or model

**"SMTP authentication failed"**
- Verify email/password combination in Settings
- For Gmail, ensure you're using an App Password (not your account password)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

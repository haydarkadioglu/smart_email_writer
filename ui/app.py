import os
import streamlit as st

from services.email_sender import EmailSender
from services.excel_logger import ExcelLogger
from services.profile_store import ProfileStore
from clients.gemini_client import GeminiClient
from models.email_models import EmailRequest, Provider, Attachment
from config.app_config import GEMINI_MODEL


def init_services(model_name: str = GEMINI_MODEL):
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    gemini_client = GeminiClient(api_key=gemini_api_key, model_name=model_name)
    email_sender = EmailSender()
    excel_logger = ExcelLogger()
    profile_store = ProfileStore()
    return gemini_client, email_sender, excel_logger, profile_store


def run_app():
    st.set_page_config(page_title="Smart Email Writer", page_icon="✉️", layout="centered")

    # Model selection
    model_choice = st.selectbox(
        "Gemini Model",
        options=["gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-1.5-pro"],
        index=0,
        help="2.0-flash-lite is newest and fastest, Pro is most capable"
    )
    
    gemini_client, email_sender, excel_logger, profile_store = init_services(model_name=model_choice)

    # Defaults from environment
    env_provider = (os.getenv("SMTP_PROVIDER", "gmail") or "gmail").lower()
    default_provider = Provider.GMAIL if env_provider == "gmail" else Provider.OUTLOOK
    default_email = os.getenv("SMTP_EMAIL", "")
    default_password = os.getenv("SMTP_PASSWORD", "")

    st.title("Smart Email Writer ✨")
    st.caption("Gemini-powered email generator with Gmail/Outlook sending and Excel logging")

    with st.sidebar:
        st.header("SMTP Settings")
        provider_label = st.selectbox(
            "Provider",
            options=["Gmail", "Outlook"],
            index=(0 if default_provider == Provider.GMAIL else 1),
        )
        provider = Provider.GMAIL if provider_label == "Gmail" else Provider.OUTLOOK
        smtp_email = st.text_input("Your Email (sender)", value=default_email, placeholder="name@example.com")
        smtp_password = st.text_input("SMTP Password/App Password", value=default_password, type="password")
        st.info("We do not store your credentials. Used only to send during this session.")

    with st.expander("Your Profile (used for drafts)", expanded=False):
        current_profile = profile_store.load()
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name", value=current_profile.get("name", ""))
            title = st.text_input("Title/Position", value=current_profile.get("title", ""))
            company = st.text_input("Company", value=current_profile.get("company", ""))
            experience = st.text_input("Years of Experience", value=current_profile.get("experience", ""))
            location = st.text_input("Location", value=current_profile.get("location", ""))
        
        with col2:
            phone = st.text_input("Phone", value=current_profile.get("phone", ""))
            email = st.text_input("Email", value=current_profile.get("email", ""))
            website = st.text_input("Website/Portfolio", value=current_profile.get("website", ""))
            linkedin = st.text_input("LinkedIn", value=current_profile.get("linkedin", ""))
            github = st.text_input("GitHub", value=current_profile.get("github", ""))
        
        skills = st.text_area("Skills (comma or line separated)", value=current_profile.get("skills", ""), height=80)
        summary = st.text_area("Professional Summary", value=current_profile.get("summary", ""), height=100, 
                              placeholder="Brief description of your background and expertise")
        achievements = st.text_area("Key Achievements", value=current_profile.get("achievements", ""), height=80,
                                   placeholder="Notable accomplishments, projects, or certifications")
        
        colp1, colp2 = st.columns([1, 1])
        with colp1:
            if st.button("Save Profile", use_container_width=True):
                profile_store.save({
                    "name": name,
                    "title": title,
                    "company": company,
                    "experience": experience,
                    "location": location,
                    "phone": phone,
                    "email": email,
                    "website": website,
                    "linkedin": linkedin,
                    "github": github,
                    "skills": skills,
                    "summary": summary,
                    "achievements": achievements,
                })
                st.success("Profile saved")
        with colp2:
            if st.button("Reload Profile", use_container_width=True):
                st.experimental_rerun()

    st.subheader("Generate Email")
    purpose = st.text_input("Purpose/Topic", placeholder="Follow-up meeting request about Q4 roadmap")
    recipient = st.text_input("Recipient Name", placeholder="Jane Doe")
    recipient_email = st.text_input("Recipient Email", placeholder="jane@example.com")

    col_gen1, col_gen2, col_gen3 = st.columns(3)
    with col_gen1:
        tone = st.selectbox("Tone", ["Professional", "Friendly", "Concise", "Detailed"], index=0)
    with col_gen2:
        language = st.selectbox("Language", ["English", "Turkish", "German", "French", "Spanish"], index=1)
    with col_gen3:
        email_length = st.selectbox("Email Length", ["Short (1-2 paragraphs)", "Medium (3-4 paragraphs)", "Long (5+ paragraphs)"], index=1)

    additional_context = st.text_area(
        "Additional Context",
        placeholder=(
            "Key points, constraints, deadlines, links, or any details to guide the model."
        ),
        height=120,
    )

    uploaded_files = st.file_uploader("Attachments (optional)", accept_multiple_files=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generate with Gemini", use_container_width=True):
            with st.spinner("Generating email draft..."):
            generated = gemini_client.generate_email(
                purpose=purpose,
                recipient_name=recipient,
                tone=tone,
                language=language,
                additional_context=additional_context,
                profile=profile_store.load(),
                email_length=email_length,
            )
                st.session_state["generated_email_body"] = generated.body
                st.session_state["generated_subject"] = generated.subject

    with col2:
        if st.button("Clear Draft", use_container_width=True):
            st.session_state["generated_email_body"] = ""
            st.session_state["generated_subject"] = ""

    subject_default = st.session_state.get("generated_subject", "")
    body_default = st.session_state.get("generated_email_body", "")

    subject = st.text_input("Subject", value=subject_default)
    body = st.text_area("Body", value=body_default, height=280)

    send_col1, send_col2 = st.columns([1, 1])
    with send_col1:
        attach_log = st.checkbox("Log to Excel after send", value=True)
    with send_col2:
        send_btn = st.button("Send Email ✉️", type="primary", use_container_width=True)

    if send_btn:
        attachments = None
        if uploaded_files:
            attachments = []
            for uf in uploaded_files:
                content = uf.read()
                mime = uf.type or "application/octet-stream"
                attachments.append(Attachment(filename=uf.name, content=content, mime_type=mime))

        request = EmailRequest(
            provider=provider,
            sender_email=smtp_email,
            sender_password=smtp_password,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            attachments=attachments,
        )
        with st.spinner("Sending email..."):
            ok, error_message = email_sender.send(request)
        if ok:
            st.success("Email sent successfully.")
            if attach_log:
                try:
                    excel_logger.append(
                        sender_email=smtp_email,
                        recipient_email=recipient_email,
                        subject=subject,
                        body=body,
                        provider=provider.name,
                    )
                    st.toast("Logged to Excel.")
                except Exception as e:
                    st.warning(f"Sent but failed to log: {e}")
        else:
            st.error(f"Failed to send: {error_message}")

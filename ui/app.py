import os
import streamlit as st

from services.email_sender import EmailSender
from services.excel_logger import ExcelLogger
from services.profile_store import ProfileStore
from services.settings_store import SettingsStore
from services.file_parser import FileParser
from services.bulk_email_sender import BulkEmailSender
from clients.gemini_client import GeminiClient
from clients.groq_client import GroqClient
from models.email_models import EmailRequest, Provider, Attachment, BulkEmailRequest, RecipientData
from config.app_config import GEMINI_MODEL
from config.app_config import GROQ_MODEL


def _send_bulk_emails_direct(bulk_request, delay_seconds, bulk_log_excel, bulk_email_sender, profile_store):
    """Send bulk emails directly without approval workflow."""
    # Validate request
    is_valid, validation_errors = bulk_email_sender.validate_bulk_request(bulk_request)
    if not is_valid:
        st.error("Validation errors:")
        for error in validation_errors:
            st.text(f"• {error}")
        return
    
    # Create progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def progress_callback(current, total, recipient_name, success, generation_method="Template"):
        progress = current / total
        progress_bar.progress(progress)
        status = "✅" if success else "❌"
        method_icon = "🤖" if generation_method == "AI" else "📝" if generation_method == "Template" else "❌"
        status_text.text(f"{status} {method_icon} {recipient_name} ({current}/{total}) - {generation_method}")
    
    # Send bulk emails
    with st.spinner("Sending bulk emails..."):
        results = bulk_email_sender.send_bulk_emails(
            bulk_request,
            delay_seconds=delay_seconds,
            log_to_excel=bulk_log_excel,
            progress_callback=progress_callback,
            profile=profile_store.load()
        )
    
    # Show results
    progress_bar.progress(1.0)
    status_text.text("✅ Bulk email sending completed!")
    
    # Display summary
    col_result1, col_result2, col_result3 = st.columns(3)
    with col_result1:
        st.metric("Total Recipients", results['total_recipients'])
    with col_result2:
        st.metric("Successful", results['successful_sends'], delta=f"+{results['successful_sends']}")
    with col_result3:
        st.metric("Failed", results['failed_sends'], delta=f"-{results['failed_sends']}")
    
    if results['errors']:
        with st.expander("❌ Failed Emails Details", expanded=False):
            for error in results['errors']:
                st.text(f"• {error}")
    
    if results['successful_sends'] > 0:
        st.success(f"🎉 Successfully sent {results['successful_sends']} emails!")
        if bulk_log_excel:
            st.toast("📊 Emails logged to Excel")


def _handle_approval_workflow(bulk_email_sender, profile_store, file_parser):
    """Handle the approval workflow for bulk emails."""
    workflow = st.session_state["approval_workflow"]
    current_index = workflow["current_index"]
    recipients = workflow["recipients"]
    bulk_request = workflow["bulk_request"]
    
    if current_index >= len(recipients):
        # All emails processed
        st.success("🎉 All emails have been processed!")
        
        # Show final results
        results = workflow["results"]
        col_result1, col_result2, col_result3 = st.columns(3)
        with col_result1:
            st.metric("Total Recipients", len(recipients))
        with col_result2:
            st.metric("Successful", results['successful_sends'], delta=f"+{results['successful_sends']}")
        with col_result3:
            st.metric("Failed", results['failed_sends'], delta=f"-{results['failed_sends']}")
        
        if results['errors']:
            with st.expander("❌ Failed Emails Details", expanded=False):
                for error in results['errors']:
                    st.text(f"• {error}")
        
        # Reset workflow
        if st.button("Start New Bulk Email", type="primary"):
            st.session_state["approval_workflow"]["active"] = False
            st.rerun()
        
        return
    
    # Show current email preview
    current_recipient = recipients[current_index]
    st.subheader(f"📧 Email Preview ({current_index + 1}/{len(recipients)})")
    
    # Progress bar
    progress = (current_index + 1) / len(recipients)
    st.progress(progress)
    
    # Show current status
    col_status1, col_status2, col_status3 = st.columns(3)
    with col_status1:
        st.metric("Processed", current_index)
    with col_status2:
        st.metric("Successful", workflow["results"]["successful_sends"])
    with col_status3:
        st.metric("Failed/Skipped", workflow["results"]["failed_sends"])
    
    # Generate email content for preview
    if bulk_request.use_ai_generation and bulk_email_sender.ai_client:
        try:
            ai_subject, ai_body = bulk_email_sender._generate_ai_email(
                bulk_request, current_recipient, profile_store.load()
            )
            preview_subject = ai_subject
            preview_body = ai_body
            generation_method = "AI Generated"
        except Exception as e:
            st.error(f"AI generation failed: {str(e)}")
            preview_subject = bulk_email_sender._personalize_email_body(bulk_request.subject, current_recipient)
            preview_body = bulk_email_sender._personalize_email_body(bulk_request.body_template, current_recipient)
            generation_method = "Template (AI failed)"
    else:
        preview_subject = bulk_email_sender._personalize_email_body(bulk_request.subject, current_recipient)
        preview_body = bulk_email_sender._personalize_email_body(bulk_request.body_template, current_recipient)
        generation_method = "Template"
    
    # Show email preview with editing capability - FULL WIDTH
    st.write("**📧 Subject:**")
    edited_subject = st.text_input("", value=preview_subject, key=f"subject_{current_index}", placeholder="Enter email subject...")
    
    st.write("**📝 Email Body:**")
    edited_body = st.text_area("", value=preview_body, height=400, key=f"body_{current_index}", placeholder="Enter email body...")
    
    # Show recipient details in expandable sections
    with st.expander("👤 Recipient Details", expanded=False):
        col_detail1, col_detail2 = st.columns(2)
        with col_detail1:
            st.write(f"**Name:** {current_recipient.name}")
            st.write(f"**Email:** {current_recipient.email}")
            st.write(f"**Description:** {current_recipient.description}")
        with col_detail2:
            st.write(f"**Generation Method:** {generation_method}")
            if current_recipient.custom_fields:
                st.write("**Custom Fields:**")
                for field_name, field_value in current_recipient.custom_fields.items():
                    st.write(f"  - **{field_name}:** {field_value}")
    
    # Show email statistics
    with st.expander("📊 Email Statistics", expanded=False):
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Subject Length", len(edited_subject))
        with col_stat2:
            st.metric("Body Length", len(edited_body))
        with col_stat3:
            st.metric("Word Count", len(edited_body.split()))
    
    # Approval buttons
    col_approve1, col_approve2, col_approve3, col_approve4 = st.columns(4)
    
    with col_approve1:
        if st.button("✅ Approve & Send", type="primary", use_container_width=True):
            # Send this email with edited content
            try:
                email_request = EmailRequest(
                    provider=bulk_request.provider,
                    sender_email=bulk_request.sender_email,
                    sender_password=bulk_request.sender_password,
                    recipient_email=current_recipient.email,
                    subject=edited_subject,
                    body=edited_body,
                    attachments=bulk_request.attachments
                )
                
                success, error_message = bulk_email_sender.email_sender.send(email_request)
                
                if success:
                    workflow["results"]["successful_sends"] += 1
                    workflow["results"]["sent_emails"].append({
                        'recipient_name': current_recipient.name,
                        'recipient_email': current_recipient.email,
                        'subject': edited_subject
                    })
                    
                    # Log to Excel if enabled
                    if workflow["log_to_excel"]:
                        try:
                            bulk_email_sender.excel_logger.append(
                                sender_email=bulk_request.sender_email,
                                recipient_email=current_recipient.email,
                                subject=edited_subject,
                                body=edited_body,
                                provider=bulk_request.provider.name,
                            )
                        except Exception as log_error:
                            st.warning(f"Failed to log: {log_error}")
                    
                    st.success(f"✅ Email sent to {current_recipient.name}")
                else:
                    workflow["results"]["failed_sends"] += 1
                    workflow["results"]["errors"].append(f"{current_recipient.name}: {error_message}")
                    st.error(f"❌ Failed to send to {current_recipient.name}: {error_message}")
                
                # Move to next email
                workflow["current_index"] += 1
                st.rerun()
                
            except Exception as e:
                st.error(f"Error sending email: {str(e)}")
    
    with col_approve2:
        if st.button("⏭️ Skip This", use_container_width=True):
            workflow["results"]["failed_sends"] += 1
            workflow["results"]["errors"].append(f"{current_recipient.name}: Skipped by user")
            workflow["current_index"] += 1
            st.rerun()
    
    with col_approve3:
        if st.button("⏭️⏭️ Skip All Remaining", use_container_width=True):
            # Skip all remaining emails
            remaining_count = len(recipients) - current_index
            for i in range(current_index, len(recipients)):
                workflow["results"]["failed_sends"] += 1
                workflow["results"]["errors"].append(f"{recipients[i].name}: Skipped all remaining")
            workflow["current_index"] = len(recipients)
            st.warning(f"⏭️ Skipped {remaining_count} remaining emails")
            st.rerun()
    
    with col_approve4:
        if st.button("❌ Cancel All", use_container_width=True):
            st.session_state["approval_workflow"]["active"] = False
            st.rerun()


def init_services(model_name: str = GEMINI_MODEL, provider: str = "gemini"):
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    if provider == "groq":
        ai_client = GroqClient(api_key=groq_api_key, model_name=model_name)
    else:
        ai_client = GeminiClient(api_key=gemini_api_key, model_name=model_name)
    email_sender = EmailSender()
    excel_logger = ExcelLogger()
    profile_store = ProfileStore()
    file_parser = FileParser()
    bulk_email_sender = BulkEmailSender(ai_client=ai_client)
    return ai_client, email_sender, excel_logger, profile_store, file_parser, bulk_email_sender


def run_app():
    st.set_page_config(page_title="Smart Email Writer", page_icon="✉️", layout="centered")

    # Load persisted UI defaults
    settings_store = SettingsStore()
    settings = settings_store.load()
    default_ai_provider = settings.get("ai_provider", "gemini")

    # Provider + Model selection
    provider_options = ["gemini", "groq"]
    try:
        provider_index = provider_options.index(default_ai_provider)
    except ValueError:
        provider_index = 0
    ai_provider = st.selectbox(
        "AI Provider",
        options=provider_options,
        index=provider_index,
        help="Choose AI backend",
    )

    if ai_provider == "groq":
        if not os.getenv("GROQ_API_KEY"):
            st.warning("GROQ_API_KEY is not set. Requests will fail. Add it to your .env and restart.")
        groq_default = settings.get("groq_model", GROQ_MODEL)
        model_choice = st.text_input(
            "Groq Model",
            value=groq_default,
            help="Enter any Groq model id (e.g., llama-3.1-70b-versatile)",
        )
    else:
        gemini_models = ["gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-1.5-pro"]
        gemini_default = settings.get("gemini_model", GEMINI_MODEL)
        try:
            gemini_index = gemini_models.index(gemini_default)
        except ValueError:
            gemini_index = 0
        model_choice = st.selectbox(
            "Gemini Model",
            options=gemini_models,
            index=gemini_index,
            help="2.0-flash-lite is newest and fastest, Pro is most capable",
        )

    # Save defaults control
    col_sd1, col_sd2 = st.columns([1, 3])
    with col_sd1:
        if st.button("Save as default"):
            new_settings = {
                "ai_provider": ai_provider,
            }
            if ai_provider == "groq":
                new_settings["groq_model"] = model_choice
            else:
                new_settings["gemini_model"] = model_choice
            settings_store.save({**settings, **new_settings})
            st.success("Defaults saved")

    ai_client, email_sender, excel_logger, profile_store, file_parser, bulk_email_sender = init_services(model_name=model_choice, provider=ai_provider)

    # Defaults from environment
    env_provider = (os.getenv("SMTP_PROVIDER", "gmail") or "gmail").lower()
    default_provider = Provider.GMAIL if env_provider == "gmail" else Provider.OUTLOOK
    default_email = os.getenv("SMTP_EMAIL", "")
    default_password = os.getenv("SMTP_PASSWORD", "")

    st.title("Smart Email Writer ✨")
    st.caption("AI-powered email generator with Gmail/Outlook sending and Excel logging")

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
    purpose_default = settings.get("default_purpose", "")
    purpose = st.text_input("Purpose/Topic", value=purpose_default, placeholder="Follow-up meeting request about Q4 roadmap")
    save_purpose = st.button("Save Purpose")
    if save_purpose:
        settings_store.save({**settings, "default_purpose": purpose})
        st.success("Purpose saved")
    recipient = st.text_input("Recipient Name", placeholder="Jane Doe")
    recipient_email = st.text_input("Recipient Email", placeholder="jane@example.com")

    col_gen1, col_gen2, col_gen3 = st.columns(3)
    with col_gen1:
        tone = st.selectbox("Tone", ["Professional", "Friendly", "Concise", "Detailed"], index=0)
    with col_gen2:
        language = st.selectbox("Language", ["English", "Turkish", "German", "French", "Spanish"], index=1)
    with col_gen3:
        email_length = st.selectbox("Email Length", ["Very Short (1 paragraph)", "Short (1-2 paragraphs)", "Medium (3-4 paragraphs)", "Long (5+ paragraphs)", "Ultra Short (~700 chars)"], index=2)

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
        if st.button("Generate with AI", use_container_width=True):
            with st.spinner("Generating email draft..."):
                try:
                    generated = ai_client.generate_email(
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
                except Exception as e:
                    st.error(str(e))

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

    # Bulk Email Section
    st.divider()
    st.subheader("📧 Bulk Email")
    st.caption("Send personalized emails to multiple recipients from CSV/Excel files")
    
    # File upload section
    uploaded_file = st.file_uploader(
        "Upload CSV or Excel file", 
        type=['csv', 'xlsx', 'xls'],
        help="File should contain columns for recipient names, emails, and descriptions"
    )
    
    if uploaded_file is not None:
        try:
            # Get file columns
            file_columns = file_parser.get_file_columns(uploaded_file.getvalue(), uploaded_file.name)
            
            st.success(f"File loaded successfully! Found {len(file_columns)} columns.")
            
            # Column mapping section
            st.subheader("📋 Column Mapping")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                name_column = st.selectbox(
                    "Name Column",
                    options=file_columns,
                    help="Select the column containing recipient names"
                )
            
            with col2:
                email_column = st.selectbox(
                    "Email Column", 
                    options=file_columns,
                    help="Select the column containing email addresses"
                )
            
            with col3:
                description_column = st.selectbox(
                    "Description Column",
                    options=file_columns,
                    help="Select the column containing descriptions or additional info"
                )
            
            # Custom columns mapping
            st.subheader("🔧 Custom Fields (Optional)")
            st.caption("Map additional columns to custom fields for personalization")
            
            custom_columns = {}
            remaining_columns = [col for col in file_columns if col not in [name_column, email_column, description_column]]
            
            if remaining_columns:
                for i, col in enumerate(remaining_columns[:5]):  # Limit to 5 custom fields
                    field_name = st.text_input(
                        f"Field name for '{col}'",
                        value=col.lower().replace(' ', '_'),
                        key=f"custom_field_{i}",
                        help=f"Use this name in your email template as {{{col.lower().replace(' ', '_')}}}"
                    )
                    if field_name:
                        custom_columns[field_name] = col
            
            # Preview data
            if st.button("Preview Data", type="secondary"):
                try:
                    preview_data, total_rows = file_parser.preview_data(
                        uploaded_file.getvalue(),
                        uploaded_file.name,
                        name_column,
                        email_column,
                        description_column,
                        custom_columns if custom_columns else None
                    )
                    
                    st.subheader(f"📊 Data Preview ({total_rows} total rows)")
                    st.dataframe(preview_data, use_container_width=True)
                    
                    # Store parsed data in session state
                    st.session_state["bulk_recipients"] = file_parser.parse_file(
                        uploaded_file.getvalue(),
                        uploaded_file.name,
                        name_column,
                        email_column,
                        description_column,
                        custom_columns if custom_columns else None
                    )
                    st.session_state["bulk_custom_columns"] = custom_columns
                    
                except Exception as e:
                    st.error(f"Error previewing data: {str(e)}")
            
            # Bulk email composition
            if "bulk_recipients" in st.session_state:
                st.subheader("✍️ Bulk Email Composition")
                
                # AI Generation Toggle
                col_ai1, col_ai2 = st.columns([1, 2])
                with col_ai1:
                    use_ai_generation = st.checkbox(
                        "🤖 Use AI Generation", 
                        value=False,
                        help="Generate personalized emails using AI for each recipient"
                    )
                
                with col_ai2:
                    if use_ai_generation:
                        st.info("AI will generate unique emails for each recipient based on their data")
                    else:
                        st.info("Use template-based personalization with placeholders")
                
                if use_ai_generation:
                    # AI Generation Settings
                    st.subheader("🤖 AI Generation Settings")
                    
                    col_ai_settings1, col_ai_settings2 = st.columns(2)
                    with col_ai_settings1:
                        ai_purpose = st.text_input(
                            "AI Purpose/Topic",
                            placeholder="Follow-up meeting request about Q4 roadmap",
                            help="What should the AI generate emails about?"
                        )
                        ai_tone = st.selectbox(
                            "AI Tone", 
                            ["Professional", "Friendly", "Concise", "Detailed"], 
                            index=0
                        )
                        ai_language = st.selectbox(
                            "AI Language", 
                            ["English", "Turkish", "German", "French", "Spanish"], 
                            index=1
                        )
                    
                    with col_ai_settings2:
                        ai_length = st.selectbox(
                            "AI Email Length", 
                            ["Very Short (1 paragraph)", "Short (1-2 paragraphs)", "Medium (3-4 paragraphs)", "Long (5+ paragraphs)", "Ultra Short (~700 chars)"], 
                            index=2
                        )
                        ai_additional_context = st.text_area(
                            "AI Additional Context",
                            placeholder="Key points, constraints, deadlines, or any details to guide the AI model",
                            height=100
                        )
                    
                    # AI will generate both subject and body
                    bulk_subject = "AI Generated"  # Placeholder for AI generation
                    bulk_body_template = "AI Generated"  # Placeholder for AI generation
                    
                    st.info("💡 AI will generate both subject and body for each recipient based on their individual data and your settings.")
                
                else:
                    # Template-based composition
                    st.subheader("📝 Template-based Composition")
                    
                    # Email template with placeholders
                    bulk_subject = st.text_input(
                        "Email Subject",
                        placeholder="Meeting Request - {name}",
                        help="Use {name}, {email}, {description} and custom fields for personalization"
                    )
                    
                    bulk_body_template = st.text_area(
                        "Email Body Template",
                        height=200,
                        placeholder="""Dear {name},

I hope this email finds you well. I wanted to reach out regarding {description}.

Best regards,
Your Name""",
                        help="Use placeholders like {name}, {email}, {description} and your custom fields"
                    )
                
                # Bulk email settings
                col_bulk1, col_bulk2, col_bulk3 = st.columns(3)
                with col_bulk1:
                    delay_seconds = st.number_input(
                        "Delay between emails (seconds)",
                        min_value=0.0,
                        max_value=10.0,
                        value=1.0,
                        step=0.1,
                        help="Delay to avoid rate limiting"
                    )
                
                with col_bulk2:
                    bulk_log_excel = st.checkbox("Log to Excel after sending", value=True)
                
                with col_bulk3:
                    require_approval = st.checkbox(
                        "Require approval for each email", 
                        value=False,
                        help="Preview and approve each email before sending"
                    )
                
                # Show recipient count and estimated time
                recipient_count = len(st.session_state["bulk_recipients"])
                estimated_time = bulk_email_sender.get_estimated_send_time(recipient_count, delay_seconds)
                
                if require_approval:
                    st.info(f"📊 **{recipient_count} recipients** | ⏱️ **Estimated time: {estimated_time}** | ⚠️ **Approval required for each email**")
                else:
                    st.info(f"📊 **{recipient_count} recipients** | ⏱️ **Estimated time: {estimated_time}**")
                
                # Validate recipients
                valid_recipients, invalid_emails = file_parser.validate_email_addresses(st.session_state["bulk_recipients"])
                
                if invalid_emails:
                    st.warning(f"⚠️ **{len(invalid_emails)} invalid email addresses found:**")
                    for invalid in invalid_emails[:5]:  # Show first 5
                        st.text(f"• {invalid}")
                    if len(invalid_emails) > 5:
                        st.text(f"• ... and {len(invalid_emails) - 5} more")
                
                # Initialize approval workflow session state
                if "approval_workflow" not in st.session_state:
                    st.session_state["approval_workflow"] = {
                        "active": False,
                        "current_index": 0,
                        "recipients": [],
                        "bulk_request": None,
                        "delay_seconds": 0,
                        "log_to_excel": True,
                        "results": {"successful_sends": 0, "failed_sends": 0, "errors": [], "sent_emails": [], "failed_emails": []}
                    }
                
                # Send bulk emails
                col_send1, col_send2 = st.columns([1, 1])
                with col_send1:
                    if not st.session_state["approval_workflow"]["active"]:
                        if st.button("Send Bulk Emails 🚀", type="primary", use_container_width=True):
                            # Validation
                            if not use_ai_generation and (not bulk_subject.strip() or not bulk_body_template.strip()):
                                st.error("Please fill in both subject and body template")
                            elif use_ai_generation and not ai_purpose.strip():
                                st.error("Please provide AI purpose/topic for email generation")
                            elif not valid_recipients:
                                st.error("No valid recipients found. Please check your email addresses.")
                            else:
                                # Create bulk email request
                                bulk_request = BulkEmailRequest(
                                    provider=provider,
                                    sender_email=smtp_email,
                                    sender_password=smtp_password,
                                    subject=bulk_subject,
                                    body_template=bulk_body_template,
                                    recipients=valid_recipients,
                                    attachments=None,
                                    use_ai_generation=use_ai_generation,
                                    ai_purpose=ai_purpose if use_ai_generation else "",
                                    ai_tone=ai_tone if use_ai_generation else "Professional",
                                    ai_language=ai_language if use_ai_generation else "English",
                                    ai_length=ai_length if use_ai_generation else "Medium (3-4 paragraphs)",
                                    ai_additional_context=ai_additional_context if use_ai_generation else ""
                                )
                                
                                if require_approval:
                                    # Start approval workflow
                                    st.session_state["approval_workflow"] = {
                                        "active": True,
                                        "current_index": 0,
                                        "recipients": valid_recipients,
                                        "bulk_request": bulk_request,
                                        "delay_seconds": delay_seconds,
                                        "log_to_excel": bulk_log_excel,
                                        "results": {"successful_sends": 0, "failed_sends": 0, "errors": [], "sent_emails": [], "failed_emails": []}
                                    }
                                    st.rerun()
                                else:
                                    # Send directly without approval
                                    _send_bulk_emails_direct(bulk_request, delay_seconds, bulk_log_excel, bulk_email_sender, profile_store)
                    else:
                        # Approval workflow is active
                        _handle_approval_workflow(bulk_email_sender, profile_store, file_parser)
                
                with col_send2:
                    if st.button("Clear Bulk Data", use_container_width=True):
                        if "bulk_recipients" in st.session_state:
                            del st.session_state["bulk_recipients"]
                        if "bulk_custom_columns" in st.session_state:
                            del st.session_state["bulk_custom_columns"]
                        st.rerun()
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
    
    # Bulk email help section
    with st.expander("ℹ️ Bulk Email Help", expanded=False):
        st.markdown("""
        **How to use Bulk Email:**
        
        1. **Prepare your file**: Create a CSV or Excel file with columns for:
           - Recipient names
           - Email addresses  
           - Descriptions or additional info
           - Any custom fields you want to use
        
        2. **Upload and map columns**: Select which columns contain the required data
        
        3. **Add custom fields**: Map additional columns to custom field names for personalization
        
        4. **Preview your data**: Check that everything looks correct before sending
        
        5. **Choose generation method**:
           - **🤖 AI Generation**: AI creates unique emails for each recipient based on their data
           - **📝 Template-based**: Use placeholders like `{name}`, `{email}`, `{description}`, `{custom_field}`
        
        6. **Send**: The system will personalize each email and send them with delays to avoid rate limiting
        
        **AI Generation Features:**
        - Each recipient gets a unique, personalized email
        - AI uses recipient data (name, description, custom fields) for personalization
        - Choose tone, language, and length for all generated emails
        - Fallback to template if AI generation fails
        
        **Tips:**
        - Use delays between emails to avoid being flagged as spam
        - Test with a small group first
        - Check your email addresses for validity
        - Use meaningful custom field names for better personalization
        - AI generation takes longer but creates more personalized content
        """)

import time
from typing import List, Tuple, Dict, Optional, Callable
from models.email_models import BulkEmailRequest, RecipientData, EmailRequest, Provider, Attachment
from services.email_sender import EmailSender
from services.excel_logger import ExcelLogger


class BulkEmailSender:
    """Service for sending bulk emails to multiple recipients."""
    
    def __init__(self, ai_client=None):
        self.email_sender = EmailSender()
        self.excel_logger = ExcelLogger()
        self.ai_client = ai_client
    
    def _generate_ai_email(self, request: BulkEmailRequest, recipient: RecipientData, profile: dict) -> Tuple[str, str]:
        """
        Generate personalized email using AI for a specific recipient.
        
        Args:
            request: BulkEmailRequest containing AI settings
            recipient: RecipientData for personalization
            profile: User profile for AI context
        
        Returns:
            Tuple of (subject, body)
        """
        if not self.ai_client:
            raise Exception("AI client not available for email generation")
        
        # Create personalized context for this recipient
        personalized_context = f"Recipient: {recipient.name} ({recipient.email})\n"
        personalized_context += f"Description: {recipient.description}\n"
        
        if recipient.custom_fields:
            personalized_context += "Additional recipient information:\n"
            for field_name, field_value in recipient.custom_fields.items():
                personalized_context += f"- {field_name}: {field_value}\n"
        
        # Add the original additional context
        if request.ai_additional_context:
            personalized_context += f"\nAdditional context: {request.ai_additional_context}"
        
        try:
            generated = self.ai_client.generate_email(
                purpose=request.ai_purpose,
                recipient_name=recipient.name,
                tone=request.ai_tone,
                language=request.ai_language,
                additional_context=personalized_context,
                profile=profile,
                email_length=request.ai_length,
            )
            return generated.subject, generated.body
        except Exception as e:
            raise Exception(f"AI generation failed for {recipient.name}: {str(e)}")

    def send_bulk_emails(self, request: BulkEmailRequest, 
                        delay_seconds: float = 1.0,
                        log_to_excel: bool = True,
                        progress_callback=None,
                        profile: dict = None) -> Dict[str, any]:
        """
        Send bulk emails to multiple recipients.
        
        Args:
            request: BulkEmailRequest containing all email details
            delay_seconds: Delay between emails to avoid rate limiting
            log_to_excel: Whether to log sent emails to Excel
            progress_callback: Optional callback function for progress updates
        
        Returns:
            Dictionary with results summary
        """
        results = {
            'total_recipients': len(request.recipients),
            'successful_sends': 0,
            'failed_sends': 0,
            'errors': [],
            'sent_emails': [],
            'failed_emails': []
        }
        
        for i, recipient in enumerate(request.recipients):
            try:
                # Generate email content
                if request.use_ai_generation and self.ai_client and profile:
                    # Use AI to generate personalized email
                    try:
                        ai_subject, ai_body = self._generate_ai_email(request, recipient, profile)
                        final_subject = ai_subject
                        final_body = ai_body
                    except Exception as ai_error:
                        # Fallback to template if AI generation fails
                        final_subject = self._personalize_email_body(request.subject, recipient)
                        final_body = self._personalize_email_body(request.body_template, recipient)
                        results['errors'].append(f"AI generation failed for {recipient.name}, using template: {str(ai_error)}")
                else:
                    # Use template-based personalization
                    final_subject = self._personalize_email_body(request.subject, recipient)
                    final_body = self._personalize_email_body(request.body_template, recipient)
                
                # Create individual email request
                email_request = EmailRequest(
                    provider=request.provider,
                    sender_email=request.sender_email,
                    sender_password=request.sender_password,
                    recipient_email=recipient.email,
                    subject=final_subject,
                    body=final_body,
                    attachments=request.attachments
                )
                
                # Send email
                success, error_message = self.email_sender.send(email_request)
                
                if success:
                    results['successful_sends'] += 1
                    results['sent_emails'].append({
                        'recipient_name': recipient.name,
                        'recipient_email': recipient.email,
                        'subject': final_subject
                    })
                    
                    # Log to Excel if enabled
                    if log_to_excel:
                        try:
                            self.excel_logger.append(
                                sender_email=request.sender_email,
                                recipient_email=recipient.email,
                                subject=final_subject,
                                body=final_body,
                                provider=request.provider.name,
                            )
                        except Exception as log_error:
                            print(f"Warning: Failed to log email for {recipient.email}: {log_error}")
                else:
                    results['failed_sends'] += 1
                    results['errors'].append(f"{recipient.name} ({recipient.email}): {error_message}")
                    results['failed_emails'].append({
                        'recipient_name': recipient.name,
                        'recipient_email': recipient.email,
                        'error': error_message
                    })
                
                # Call progress callback if provided
                if progress_callback:
                    generation_method = "AI" if (request.use_ai_generation and self.ai_client and profile) else "Template"
                    progress_callback(i + 1, len(request.recipients), recipient.name, success, generation_method)
                
                # Add delay between emails to avoid rate limiting
                if delay_seconds > 0 and i < len(request.recipients) - 1:
                    time.sleep(delay_seconds)
                    
            except Exception as e:
                results['failed_sends'] += 1
                error_msg = f"Unexpected error for {recipient.name} ({recipient.email}): {str(e)}"
                results['errors'].append(error_msg)
                results['failed_emails'].append({
                    'recipient_name': recipient.name,
                    'recipient_email': recipient.email,
                    'error': str(e)
                })
                
                if progress_callback:
                    progress_callback(i + 1, len(request.recipients), recipient.name, False, "Error")
        
        return results
    
    def _personalize_email_body(self, template: str, recipient: RecipientData) -> str:
        """
        Personalize email body template with recipient data.
        
        Args:
            template: Email body template with placeholders
            recipient: Recipient data for personalization
        
        Returns:
            Personalized email body
        """
        personalized = template
        
        # Replace basic placeholders
        personalized = personalized.replace('{name}', recipient.name)
        personalized = personalized.replace('{email}', recipient.email)
        personalized = personalized.replace('{description}', recipient.description)
        
        # Replace custom field placeholders if they exist
        if recipient.custom_fields:
            for field_name, field_value in recipient.custom_fields.items():
                placeholder = f'{{{field_name}}}'
                personalized = personalized.replace(placeholder, str(field_value))
        
        return personalized
    
    def validate_bulk_request(self, request: BulkEmailRequest) -> Tuple[bool, List[str]]:
        """
        Validate bulk email request before sending.
        
        Args:
            request: BulkEmailRequest to validate
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Validate basic fields
        if not request.sender_email:
            errors.append("Sender email is required")
        
        # For AI generation, subject and body are generated, so don't require them
        if not request.use_ai_generation:
            if not request.subject:
                errors.append("Subject is required")
            
            if not request.body_template:
                errors.append("Email body template is required")
        else:
            # For AI generation, validate AI-specific fields
            if not request.ai_purpose:
                errors.append("AI purpose/topic is required for AI generation")
        
        if not request.recipients:
            errors.append("At least one recipient is required")
        
        # Validate recipients
        for i, recipient in enumerate(request.recipients):
            if not recipient.email:
                errors.append(f"Recipient {i+1}: Email is required")
            elif '@' not in recipient.email:
                errors.append(f"Recipient {i+1}: Invalid email format")
        
        return len(errors) == 0, errors
    
    def get_estimated_send_time(self, num_recipients: int, delay_seconds: float = 1.0) -> str:
        """
        Calculate estimated time to send all emails.
        
        Args:
            num_recipients: Number of recipients
            delay_seconds: Delay between emails
        
        Returns:
            Formatted time estimate string
        """
        if num_recipients <= 0:
            return "0 seconds"
        
        total_seconds = (num_recipients - 1) * delay_seconds
        
        if total_seconds < 60:
            return f"{total_seconds:.1f} seconds"
        elif total_seconds < 3600:
            minutes = total_seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = total_seconds / 3600
            return f"{hours:.1f} hours"

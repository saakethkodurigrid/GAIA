"""
Email service for sending invitation emails to candidates.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from services.mcq_analysis_service import generate_mcq_analysis
from services.coding_analysis_service import generate_coding_analysis
# Import pydantic first to ensure SecretStr is available for fastapi_mail
try:
    from pydantic import SecretStr  # noqa: F401
except ImportError:
    pass  # pydantic might not be installed, but that's okay

# Make error imports lazy to avoid fastapi_mail import errors at module level
_ConnectionErrors = None
_SMTPAuthenticationError = None

def _lazy_import_errors():
    """Lazy import error classes to avoid fastapi_mail import issues."""
    global _ConnectionErrors, _SMTPAuthenticationError
    if _ConnectionErrors is None:
        try:
            from fastapi_mail.errors import ConnectionErrors as _ConnErr
            from aiosmtplib.errors import SMTPAuthenticationError as _SMTPErr
            _ConnectionErrors = _ConnErr
            _SMTPAuthenticationError = _SMTPErr
        except ImportError:
            # Fallback to generic Exception if imports fail
            _ConnectionErrors = Exception
            _SMTPAuthenticationError = Exception
        except Exception:
            # Any other error, use generic Exception
            _ConnectionErrors = Exception
            _SMTPAuthenticationError = Exception
    return _ConnectionErrors, _SMTPAuthenticationError

from core.config import settings

logger = logging.getLogger(__name__)

# Lazy import to avoid import errors if fastapi_mail has issues
_fastapi_mail_imported = False
_FastMail = None
_MessageSchema = None
_ConnectionConfig = None

def _lazy_import_fastapi_mail():
    """Lazy import fastapi_mail to avoid import errors at startup."""
    global _fastapi_mail_imported, _FastMail, _MessageSchema, _ConnectionConfig
    if not _fastapi_mail_imported:
        try:
            # Try to import pydantic SecretStr first to ensure it's available
            from pydantic import SecretStr
            from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
            _FastMail = FastMail
            _MessageSchema = MessageSchema
            _ConnectionConfig = ConnectionConfig
            _fastapi_mail_imported = True
        except ImportError as e:
            logger.error(f"Failed to import fastapi_mail dependencies: {e}. Email functionality will be disabled.")
            logger.error("This may be due to a version incompatibility. Try: pip install --upgrade fastapi-mail pydantic")
            raise
        except Exception as e:
            logger.error(f"Failed to import fastapi_mail: {e}. Email functionality will be disabled.")
            raise
    return _FastMail, _MessageSchema, _ConnectionConfig


class EmailService:
    """Service for sending emails to candidates."""
    
    def __init__(self):
        """Initialize email service with configuration."""
        self.config = None
        self.fastmail = None
        self.enabled = settings.EMAIL_ENABLED
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of fastapi_mail components."""
        if not self._initialized:
            try:
                FastMail, _, ConnectionConfig = _lazy_import_fastapi_mail()
                self.config = ConnectionConfig(
                    MAIL_USERNAME=settings.MAIL_USERNAME,
                    MAIL_PASSWORD=settings.MAIL_PASSWORD,
                    MAIL_FROM=settings.MAIL_FROM,
                    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
                    MAIL_PORT=settings.MAIL_PORT,
                    MAIL_SERVER=settings.MAIL_SERVER,
                    MAIL_STARTTLS=settings.MAIL_STARTTLS,
                    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
                    USE_CREDENTIALS=settings.MAIL_USE_CREDENTIALS,
                    VALIDATE_CERTS=settings.MAIL_VALIDATE_CERTS,
                )
                self.fastmail = FastMail(self.config)
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize email service: {e}")
                self.enabled = False
                raise
    
    def _is_valid_email(self, email: str) -> bool:
        """
        Check if email is valid and not a placeholder.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if email is valid, False otherwise
        """
        if not email:
            return False
        
        # Check if it's a placeholder email
        if '@placeholder.com' in email.lower():
            return False
        
        # Basic email format check
        if '@' not in email or '.' not in email.split('@')[-1]:
            return False
        
        return True
    
    async def send_email_ses(
        self,
        to_addresses: List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send email using AWS SES.
        
        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Check if email is enabled
        if not self.enabled:
            logger.info(f"Email sending is disabled. Skipping email to {to_addresses}")
            return False
        
        # Validate email configuration
        if not settings.AWS_SES_REGION or not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY or not settings.AWS_SES_SOURCE_EMAIL:
            logger.warning("AWS SES configuration is incomplete. Skipping email.")
            return False
        
        # Validate recipient emails
        valid_recipients = [email for email in to_addresses if self._is_valid_email(email)]
        if not valid_recipients:
            logger.warning(f"No valid email addresses in recipients: {to_addresses}. Skipping email.")
            return False
        
        try:
            # Create SES client
            ses_client = boto3.client(
                'ses',
                region_name=settings.AWS_SES_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            
            # Prepare message body
            message_body = {
                'Html': {
                    'Data': html_body,
                    'Charset': 'UTF-8'
                }
            }
            
            # Add text body if provided
            if text_body:
                message_body['Text'] = {
                    'Data': text_body,
                    'Charset': 'UTF-8'
                }
            
            # Send email
            response = ses_client.send_email(
                Source=settings.AWS_SES_SOURCE_EMAIL,
                Destination={'ToAddresses': valid_recipients},
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': message_body
                }
            )
            
            logger.info(f"Successfully sent email via SES to {valid_recipients}. MessageId: {response.get('MessageId')}")
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Failed to send email via SES to {to_addresses}: {error_code} - {error_message}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email via SES to {to_addresses}: {str(e)}", exc_info=True)
            return False
    
    def _generate_invitation_link(self, candidate_id: str, link_type: str = "scheduling") -> str:
        """
        Generate invitation link for candidate.
        
        Args:
            candidate_id: Candidate UUID
            link_type: Type of invitation link - "scheduling" or "test"
            
        Returns:
            Invitation link URL
        """
        if link_type == "test":
            return f"{settings.FRONTEND_URL}/test/scheduled?candidate_id={candidate_id}"
        else:  # scheduling
            return f"{settings.FRONTEND_URL}/schedule?candidate_id={candidate_id}"
    
    def _create_invitation_email_html(
        self,
        candidate_name: str,
        job_role: str,
        resume_score: Optional[float],
        invitation_link: str
    ) -> str:
        """
        Create HTML email template for invitation.
        
        Args:
            candidate_name: Candidate's name
            job_role: Job role/title
            resume_score: Resume score (optional)
            invitation_link: Invitation link URL
            
        Returns:
            HTML email content
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #FFF7E5 0%, #F5FCFF 100%); padding: 30px; border-radius: 10px; margin-bottom: 20px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="text-align: center;">
                            <table cellpadding="0" cellspacing="0" style="margin: 0 auto;">
                                <tr>
                                    <td style="padding-right: 8px; vertical-align: middle;">
                                        <span style="font-size: 28px; color: #FF6B35; font-weight: bold;">&lt;/&gt;</span>
                                    </td>
                                    <td style="vertical-align: middle;">
                                        <span style="font-size: 28px; font-weight: 600; color: #0069B4;">GAIA</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </div>
            
            <div style="background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #0069B4; margin-top: 0;">Interview Invitation</h2>
                
                <p>Dear {candidate_name},</p>
                
                <p>Congratulations! We are pleased to invite you to proceed with the interview process for the position of <strong>{job_role}</strong>.</p>
                
                <p>We were impressed with your qualifications and would like to move forward with the next steps. Please click the button below to schedule your interview:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{invitation_link}" 
                       style="display: inline-block; padding: 14px 28px; background-color: #0069B4; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px;">
                        Schedule Your Interview
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
                <p style="color: #0069B4; font-size: 12px; word-break: break-all; background-color: #f5f5f5; padding: 10px; border-radius: 4px;">{invitation_link}</p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e5e5;">
                    <p style="margin: 0; color: #666; font-size: 14px;"><strong>What to expect:</strong></p>
                    <ul style="color: #666; font-size: 14px; margin: 10px 0;">
                        <li>Select a convenient date and time for your interview</li>
                        <li>Complete the interview process which includes multiple choice questions, Coding, and System Design assessments</li>
                        <li>You'll need to sign in with your Google account (please use the account associated with the email address you provided to the recruiting team) to proceed</li>
                        <li>Complete the interview process which includes multiple choice questions, Coding, and System Design assessments</li>
                        <li>You'll need to sign in with your Google account (please use the account associated with the email address you provided to the recruiting team) to proceed</li>
                    </ul>
                </div>
                
                <p style="margin-top: 30px;">We look forward to speaking with you!</p>
                
                <p>Best regards,<br>
                <strong>GAIA Team</strong></p>
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                <p>This is an automated email. Please do not reply to this message.</p>
            </div>
        </body>
        </html>
        """
        return html_content
    
    def _create_invitation_email_text(
        self,
        candidate_name: str,
        job_role: str,
        resume_score: Optional[float],
        invitation_link: str
    ) -> str:
        """
        Create plain text email template for invitation.
        
        Args:
            candidate_name: Candidate's name
            job_role: Job role/title
            resume_score: Resume score (optional)
            invitation_link: Invitation link URL
            
        Returns:
            Plain text email content
        """
        text_content = f"""
Interview Invitation - GAIA

Dear {candidate_name},

Congratulations! We are pleased to invite you to proceed with the interview process for the position of {job_role}.


We were impressed with your qualifications and would like to move forward with the next steps. Please use the link below to schedule your interview:

{invitation_link}

What to expect:
- Select a convenient date and time for your interview
- Complete the interview process which includes multiple choice questions, Coding, and System Design assessments
- You'll need to sign in with your Google account (please use the account associated with the email address you provided to the recruiting team) to proceed
- Complete the interview process which includes multiple choice questions, Coding, and System Design assessments
- You'll need to sign in with your Google account (please use the account associated with the email address you provided to the recruiting team) to proceed

We look forward to speaking with you!

Best regards,
GAIA Team

---
This is an automated email. Please do not reply to this message.
        """
        return text_content.strip()
    
    async def send_invitation_email(
        self,
        candidate_email: str,
        candidate_name: str,
        candidate_id: str,
        job_role: str,
        resume_score: Optional[float] = None
    ) -> bool:
        """
        Send invitation email to candidate.
        
        Args:
            candidate_email: Candidate's email address
            candidate_name: Candidate's name
            candidate_id: Candidate UUID
            job_role: Job role/title
            resume_score: Resume score (optional)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Check if email is enabled
        if not self.enabled:
            logger.info(f"Email sending is disabled. Skipping email to {candidate_email}")
            return False
        
        # Validate email
        if not self._is_valid_email(candidate_email):
            logger.warning(f"Invalid or placeholder email address: {candidate_email}. Skipping email.")
            return False
        
        try:
            # Generate invitation link
            invitation_link = self._generate_invitation_link(candidate_id)
            
            # Create email content
            html_content = self._create_invitation_email_html(
                candidate_name, job_role, resume_score, invitation_link
            )
            text_content = self._create_invitation_email_text(
                candidate_name, job_role, resume_score, invitation_link
            )
            
            # Send email using SES
            return self.send_email_ses(
                to_addresses=[candidate_email],
                subject=f"Interview Invitation - {job_role}",
                html_body=html_content,
                text_body=text_content
            )
            
        except Exception as e:
            logger.error(f"Error sending invitation email to {candidate_email}: {str(e)}", exc_info=True)
            return False
    
    def _create_test_invitation_email_html(
        self,
        candidate_name: str,
        job_role: str,
        scheduled_date: datetime,
        invitation_link: str
    ) -> str:
        """
        Create HTML email template for test invitation.
        
        Args:
            candidate_name: Candidate's name
            job_role: Job role/title
            scheduled_date: Scheduled test date/time
            invitation_link: Invitation link URL
            
        Returns:
            HTML email content
        """
        # Format scheduled date
        formatted_date = scheduled_date.strftime("%B %d, %Y at %I:%M %p")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #FFF7E5 0%, #F5FCFF 100%); padding: 30px; border-radius: 10px; margin-bottom: 20px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="text-align: center;">
                            <table cellpadding="0" cellspacing="0" style="margin: 0 auto;">
                                <tr>
                                    <td style="padding-right: 8px; vertical-align: middle;">
                                        <span style="font-size: 28px; color: #FF6B35; font-weight: bold;">&lt;/&gt;</span>
                                    </td>
                                    <td style="vertical-align: middle;">
                                        <span style="font-size: 28px; font-weight: 600; color: #0069B4;">GAIA</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </div>
            
            <div style="background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #0069B4; margin-top: 0;">Test Scheduled - Ready to Begin</h2>
                
                <p>Dear {candidate_name},</p>
                
                <p>Your technical interview for the position of <strong>{job_role}</strong> has been scheduled successfully!</p>
                
                <div style="margin: 20px 0; padding: 15px; background-color: #f0f9ff; border-left: 4px solid #0069B4; border-radius: 4px;">
                    <p style="margin: 0; color: #1e40af; font-weight: 600;">Scheduled Date & Time: {formatted_date}</p>
                </div>
                
                <p>You can now start your assessment by clicking the button below:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{invitation_link}" 
                       style="display: inline-block; padding: 14px 28px; background-color: #0069B4; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px;">
                        Start Your Test
                    </a>
                </div>
                
                <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
                <p style="color: #0069B4; font-size: 12px; word-break: break-all; background-color: #f5f5f5; padding: 10px; border-radius: 4px;">{invitation_link}</p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e5e5;">
                    <p style="margin: 0; color: #666; font-size: 14px;"><strong>Important Instructions:</strong></p>
                    <ul style="color: #666; font-size: 14px; margin: 10px 0;">
                        <li>Please be ready 5 minutes before the scheduled time</li>
                        <li>Ensure you have a stable internet connection</li>
                        <li>The test includes multiple choice questions, Coding, and System Design assessments</li>
                        <li>You'll need to sign in with your Google account (please use the account associated with the email address you provided to the recruiting team) to proceed</li>
                        <li>The test includes multiple choice questions, Coding, and System Design assessments</li>
                        <li>You'll need to sign in with your Google account (please use the account associated with the email address you provided to the recruiting team) to proceed</li>
                    </ul>
                </div>
                
                <p style="margin-top: 30px;">Good luck with your assessment!</p>
                
                <p>Best regards,<br>
                <strong>GAIA Team</strong></p>
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                <p>This is an automated email. Please do not reply to this message.</p>
            </div>
        </body>
        </html>
        """
        return html_content
    
    def _create_test_invitation_email_text(
        self,
        candidate_name: str,
        job_role: str,
        scheduled_date: datetime,
        invitation_link: str
    ) -> str:
        """
        Create plain text email template for test invitation.
        
        Args:
            candidate_name: Candidate's name
            job_role: Job role/title
            scheduled_date: Scheduled test date/time
            invitation_link: Invitation link URL
            
        Returns:
            Plain text email content
        """
        formatted_date = scheduled_date.strftime("%B %d, %Y at %I:%M %p")
        
        text_content = f"""
Test Scheduled - Ready to Begin - GAIA

Dear {candidate_name},

Your technical interview for the position of {job_role} has been scheduled successfully!

Scheduled Date & Time: {formatted_date}

You can now start your assessment by using the link below:

{invitation_link}

Important Instructions:
- Please be ready 5 minutes before the scheduled time
- Ensure you have a stable internet connection
- The test includes multiple choice questions, Coding, and System Design assessments
- You'll need to sign in with your Google account (please use the account associated with the email address you provided to the recruiting team) to proceed
- The test includes multiple choice questions, Coding, and System Design assessments
- You'll need to sign in with your Google account (please use the account associated with the email address you provided to the recruiting team) to proceed

Good luck with your assessment!

Best regards,
GAIA Team

---
This is an automated email. Please do not reply to this message.
        """
        return text_content.strip()
    
    async def send_scheduling_invitation_email(
        self,
        candidate_email: str,
        candidate_name: str,
        candidate_id: str,
        job_role: str,
        resume_score: float
    ) -> bool:
        """
        Send scheduling invitation email to candidate (Type 1).
        Automatically sent to candidates with resume_score >= threshold.
        
        Args:
            candidate_email: Candidate's email address
            candidate_name: Candidate's name
            candidate_id: Candidate UUID
            job_role: Job role/title
            resume_score: Resume score
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Check if email is enabled
        if not self.enabled:
            logger.info(f"Email sending is disabled. Skipping scheduling invitation email to {candidate_email}")
            return False
        
        # Validate email
        if not self._is_valid_email(candidate_email):
            logger.warning(f"Invalid or placeholder email address: {candidate_email}. Skipping email.")
            return False
        
        try:
            # Generate scheduling invitation link
            invitation_link = self._generate_invitation_link(candidate_id, link_type="scheduling")
            
            # Create email content (pass None for resume_score to not display it)
            html_content = self._create_invitation_email_html(
                candidate_name, job_role, None, invitation_link
            )
            text_content = self._create_invitation_email_text(
                candidate_name, job_role, None, invitation_link
            )
            
            # Send email using SES
            return await self.send_email_ses(
                to_addresses=[candidate_email],
                subject=f"Interview Invitation - {job_role}",
                html_body=html_content,
                text_body=text_content
            )
            
        except Exception as e:
            logger.error(f"Error sending scheduling invitation email to {candidate_email}: {str(e)}", exc_info=True)
            return False
    
    async def send_test_invitation_email(
        self,
        candidate_email: str,
        candidate_name: str,
        candidate_id: str,
        job_role: str,
        scheduled_date: datetime
    ) -> bool:
        """
        Send test invitation email to candidate (Type 2).
        Sent after candidate schedules the test.
        
        Args:
            candidate_email: Candidate's email address
            candidate_name: Candidate's name
            candidate_id: Candidate UUID
            job_role: Job role/title
            scheduled_date: Scheduled test date/time
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Check if email is enabled
        if not self.enabled:
            logger.info(f"Email sending is disabled. Skipping test invitation email to {candidate_email}")
            return False
        
        # Validate email
        if not self._is_valid_email(candidate_email):
            logger.warning(f"Invalid or placeholder email address: {candidate_email}. Skipping email.")
            return False
        
        try:
            # Generate test invitation link
            invitation_link = self._generate_invitation_link(candidate_id, link_type="test")
            
            # Create email content
            html_content = self._create_test_invitation_email_html(
                candidate_name, job_role, scheduled_date, invitation_link
            )
            text_content = self._create_test_invitation_email_text(
                candidate_name, job_role, scheduled_date, invitation_link
            )
            
            # Create subject
            formatted_date = scheduled_date.strftime("%B %d, %Y at %I:%M %p")
            subject = f"Test Scheduled - {job_role} - {formatted_date}"
            
            # Send email using SES
            return await self.send_email_ses(
                to_addresses=[candidate_email],
                subject=subject,
                html_body=html_content,
                text_body=text_content
            )
            
        except Exception as e:
            logger.error(f"Error sending test invitation email to {candidate_email}: {str(e)}", exc_info=True)
            return False
    
    def _create_recruiter_test_notification_email_html(
        self,
        recruiter_name: str,
        candidate_name: str,
        candidate_email: str,
        candidate_reference_number: Optional[str],
        job_role: str,
        scheduled_date: datetime
    ) -> str:
        """
        Create HTML email template for recruiter test notification (no test link).
        
        Args:
            recruiter_name: Recruiter's name
            candidate_name: Candidate's name
            candidate_email: Candidate's email address
            candidate_reference_number: Candidate reference (e.g., CI-123456)
            job_role: Job role/title
            scheduled_date: Scheduled test date/time
            
        Returns:
            HTML email content
        """
        # Format scheduled date
        formatted_date = scheduled_date.strftime("%B %d, %Y at %I:%M %p")
        ref_display = f" ({candidate_reference_number})" if candidate_reference_number else ""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #FFF7E5 0%, #F5FCFF 100%); padding: 30px; border-radius: 10px; margin-bottom: 20px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="text-align: center;">
                            <table cellpadding="0" cellspacing="0" style="margin: 0 auto;">
                                <tr>
                                    <td style="padding-right: 8px; vertical-align: middle;">
                                        <span style="font-size: 28px; color: #FF6B35; font-weight: bold;">&lt;/&gt;</span>
                                    </td>
                                    <td style="vertical-align: middle;">
                                        <span style="font-size: 28px; font-weight: 600; color: #0069B4;">GAIA</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </div>
            
            <div style="background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #0069B4; margin-top: 0;">Interview Scheduled - Notification</h2>
                
                <p>Dear {recruiter_name},</p>
                
                <p>This is to notify you that a technical interview has been successfully scheduled for the following candidate:</p>
                
                <div style="margin: 20px 0; padding: 20px; background-color: #f8f9fa; border-left: 4px solid #0069B4; border-radius: 4px;">
                    <p style="margin: 8px 0;"><strong style="color: #0069B4;">Candidate Name:</strong> {candidate_name}{ref_display}</p>
                    <p style="margin: 8px 0;"><strong style="color: #0069B4;">Candidate Email:</strong> {candidate_email}</p>
                    <p style="margin: 8px 0;"><strong style="color: #0069B4;">Job Role:</strong> {job_role}</p>
                    <p style="margin: 8px 0;"><strong style="color: #0069B4;">Scheduled Date & Time:</strong> {formatted_date} (IST)</p>
                    <p style="margin: 8px 0;"><strong style="color: #0069B4;">Duration:</strong> 3 hours</p>
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e5e5;">
                    <p style="margin: 0; color: #666; font-size: 14px;"><strong>Assessment Details:</strong></p>
                    <ul style="color: #666; font-size: 14px; margin: 10px 0;">
                        <li>The candidate has been sent a test invitation email with the assessment link</li>
                        <li>A calendar invite has been sent to the candidate</li>
                        <li>The assessment includes multiple choice questions, Coding, and System Design evaluations</li>
                        <li>You will be notified once the candidate completes the assessment</li>
                    </ul>
                </div>
                
                <p style="margin-top: 30px;">This is an automated notification from GAIA.</p>
                
                <p>Best regards,<br>
                <strong>GAIA Team</strong></p>
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                <p>This is an automated email. Please do not reply to this message.</p>
            </div>
        </body>
        </html>
        """
        return html_content
    
    def _create_recruiter_test_notification_email_text(
        self,
        recruiter_name: str,
        candidate_name: str,
        candidate_email: str,
        candidate_reference_number: Optional[str],
        job_role: str,
        scheduled_date: datetime
    ) -> str:
        """
        Create plain text email template for recruiter test notification.
        
        Args:
            recruiter_name: Recruiter's name
            candidate_name: Candidate's name
            candidate_email: Candidate's email address
            candidate_reference_number: Candidate reference (e.g., CI-123456)
            job_role: Job role/title
            scheduled_date: Scheduled test date/time
            
        Returns:
            Plain text email content
        """
        formatted_date = scheduled_date.strftime("%B %d, %Y at %I:%M %p")
        ref_display = f" ({candidate_reference_number})" if candidate_reference_number else ""
        
        text_content = f"""
Interview Scheduled - Notification - GAIA

Dear {recruiter_name},

This is to notify you that a technical interview has been successfully scheduled for the following candidate:

Candidate Details:
- Candidate Name: {candidate_name}{ref_display}
- Candidate Email: {candidate_email}
- Job Role: {job_role}
- Scheduled Date & Time: {formatted_date} (IST)
- Duration: 3 hours

Assessment Details:
- The candidate has been sent a test invitation email with the assessment link
- A calendar invite has been sent to the candidate
- The assessment includes multiple choice questions, Coding, and System Design evaluations
- You will be notified once the candidate completes the assessment

This is an automated notification from GAIA.

Best regards,
GAIA Team

---
This is an automated email. Please do not reply to this message.
        """
        return text_content.strip()
    
    async def send_recruiter_test_notification_email(
        self,
        recruiter_email: str,
        recruiter_name: str,
        candidate_name: str,
        candidate_email: str,
        candidate_reference_number: Optional[str],
        job_role: str,
        scheduled_date: datetime
    ) -> bool:
        """
        Send test notification email to recruiter (no test link).
        Sent when test is scheduled to notify the recruiter.
        
        Args:
            recruiter_email: Recruiter's email address
            recruiter_name: Recruiter's name
            candidate_name: Candidate's name
            candidate_email: Candidate's email address
            candidate_reference_number: Candidate reference (e.g., CI-123456)
            job_role: Job role/title
            scheduled_date: Scheduled test date/time
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Check if email is enabled
        if not self.enabled:
            logger.info(f"Email sending is disabled. Skipping recruiter notification email to {recruiter_email}")
            return False
        
        # Validate email
        if not self._is_valid_email(recruiter_email):
            logger.warning(f"Invalid or placeholder email address: {recruiter_email}. Skipping email.")
            return False
        
        try:
            # Create email content
            html_content = self._create_recruiter_test_notification_email_html(
                recruiter_name, candidate_name, candidate_email, 
                candidate_reference_number, job_role, scheduled_date
            )
            text_content = self._create_recruiter_test_notification_email_text(
                recruiter_name, candidate_name, candidate_email, 
                candidate_reference_number, job_role, scheduled_date
            )
            
            # Create subject
            subject = f"Interview Scheduled - {candidate_name} - {job_role}"
            
            # Send email using SES
            return await self.send_email_ses(
                to_addresses=[recruiter_email],
                subject=subject,
                html_body=html_content,
                text_body=text_content
            )
            
        except Exception as e:
            logger.error(f"Error sending recruiter notification email to {recruiter_email}: {str(e)}", exc_info=True)
            return False
    
    def _create_recruiter_test_completion_email_html(
        self,
        recruiter_name: str,
        candidate_name: str,
        candidate_email: str,
        candidate_reference_number: Optional[str],
        job_role: str,
        completion_date: datetime,
        overall_score: Optional[int],
        analysis_report_url: str
    ) -> str:
        """
        Create HTML email template for recruiter test completion notification.
        
        Args:
            recruiter_name: Recruiter's name
            candidate_name: Candidate's name
            candidate_email: Candidate's email address
            candidate_reference_number: Candidate reference (e.g., CI-123456)
            job_role: Job role/title
            completion_date: Test completion date/time
            overall_score: Overall test score (optional)
            analysis_report_url: Full URL to analysis report
            
        Returns:
            HTML email content
        """
        formatted_date = completion_date.strftime("%B %d, %Y at %I:%M %p")
        ref_display = f" ({candidate_reference_number})" if candidate_reference_number else ""
        
        # Score section (conditional)
        score_section = ""
        if overall_score is not None:
            score_section = f"""
            <tr>
                <td style="padding: 8px 0; font-size: 14px; color: #4B5563;">
                    <strong style="color: #1F2937;">Overall Score:</strong> {overall_score}/100
                </td>
            </tr>
            """
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Completed - {candidate_name}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #F3F4F6;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" style="max-width: 600px; margin: 0 auto; background-color: #FFFFFF; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%); padding: 40px 40px 30px; text-align: center; border-radius: 12px 12px 0 0;">
                            <h1 style="color: #FFFFFF; margin: 0; font-size: 28px; font-weight: 700;">Test Completed</h1>
                            <p style="color: #E0E7FF; margin: 10px 0 0; font-size: 16px;">Technical Assessment Notification</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <p style="margin: 0 0 20px; font-size: 16px; color: #1F2937;">Dear {recruiter_name},</p>
                            
                            <p style="margin: 0 0 30px; font-size: 16px; line-height: 1.6; color: #4B5563;">
                                The candidate has successfully completed their technical assessment. You can now review the detailed analysis report.
                            </p>
                            
                            <!-- Candidate Details Card -->
                            <div style="background-color: #F9FAFB; border-left: 4px solid #667EEA; border-radius: 6px; padding: 24px; margin-bottom: 30px;">
                                <h2 style="margin: 0 0 16px; font-size: 18px; color: #1F2937; font-weight: 600;">Candidate Details</h2>
                                <table role="presentation" style="width: 100%;">
                                    <tr>
                                        <td style="padding: 8px 0; font-size: 14px; color: #4B5563;">
                                            <strong style="color: #1F2937;">Candidate Name:</strong> {candidate_name}{ref_display}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; font-size: 14px; color: #4B5563;">
                                            <strong style="color: #1F2937;">Candidate Email:</strong> {candidate_email}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; font-size: 14px; color: #4B5563;">
                                            <strong style="color: #1F2937;">Job Role:</strong> {job_role}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; font-size: 14px; color: #4B5563;">
                                            <strong style="color: #1F2937;">Completion Date:</strong> {formatted_date} (IST)
                                        </td>
                                    </tr>
                                    {score_section}
                                </table>
                            </div>
                            
                            <!-- CTA Button -->
                            <table role="presentation" style="margin: 30px 0;">
                                <tr>
                                    <td style="text-align: center;">
                                        <a href="{analysis_report_url}" 
                                           style="display: inline-block; background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%); color: #FFFFFF; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3);">
                                            View Analysis Report
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin: 30px 0 0; font-size: 14px; color: #6B7280; text-align: center;">
                                Or copy this link: <a href="{analysis_report_url}" style="color: #667EEA; text-decoration: none;">{analysis_report_url}</a>
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #F9FAFB; padding: 30px 40px; text-align: center; border-radius: 0 0 12px 12px; border-top: 1px solid #E5E7EB;">
                            <p style="margin: 0; font-size: 14px; color: #6B7280;">
                                This is an automated email from the TechInterview Platform.
                            </p>
                            <p style="margin: 10px 0 0; font-size: 12px; color: #9CA3AF;">
                                Please do not reply to this message.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        return html_content
    
    def _create_recruiter_test_completion_email_text(
        self,
        recruiter_name: str,
        candidate_name: str,
        candidate_email: str,
        candidate_reference_number: Optional[str],
        job_role: str,
        completion_date: datetime,
        overall_score: Optional[int],
        analysis_report_url: str
    ) -> str:
        """
        Create plain text email template for recruiter test completion notification.
        
        Args:
            recruiter_name: Recruiter's name
            candidate_name: Candidate's name
            candidate_email: Candidate's email address
            candidate_reference_number: Candidate reference (e.g., CI-123456)
            job_role: Job role/title
            completion_date: Test completion date/time
            overall_score: Overall test score (optional)
            analysis_report_url: Full URL to analysis report
            
        Returns:
            Plain text email content
        """
        formatted_date = completion_date.strftime("%B %d, %Y at %I:%M %p")
        ref_display = f" ({candidate_reference_number})" if candidate_reference_number else ""
        
        # Score section (conditional)
        score_line = ""
        if overall_score is not None:
            score_line = f"\n- Overall Score: {overall_score}/100"
        
        text_content = f"""
Test Completed - Technical Assessment Notification - TechInterview Platform

Dear {recruiter_name},

The candidate has successfully completed their technical assessment. You can now review the detailed analysis report.

Candidate Details:
- Candidate Name: {candidate_name}{ref_display}
- Candidate Email: {candidate_email}
- Job Role: {job_role}
- Completion Date: {formatted_date} (IST){score_line}

View Analysis Report:
{analysis_report_url}

This is an automated email from the TechInterview Platform.

Best regards,
TechInterview Platform Team

---
This is an automated email. Please do not reply to this message.
        """
        return text_content.strip()
    
    async def send_recruiter_test_completion_email(
        self,
        recruiter_email: str,
        recruiter_name: str,
        candidate_name: str,
        candidate_email: str,
        candidate_reference_number: Optional[str],
        job_role: str,
        completion_date: datetime,
        overall_score: Optional[int],
        analysis_report_url: str
    ) -> bool:
        """
        Send test completion notification email to recruiter.
        Sent when candidate completes the test.
        
        Args:
            recruiter_email: Recruiter's email address
            recruiter_name: Recruiter's name
            candidate_name: Candidate's name
            candidate_email: Candidate's email address
            candidate_reference_number: Candidate reference (e.g., CI-123456)
            job_role: Job role/title
            completion_date: Test completion date/time
            overall_score: Overall test score (optional)
            analysis_report_url: Full URL to analysis report
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Check if email is enabled
        if not self.enabled:
            logger.info(f"Email sending is disabled. Skipping recruiter completion email to {recruiter_email}")
            return False
        
        # Validate email
        if not self._is_valid_email(recruiter_email):
            logger.warning(f"Invalid or placeholder email address: {recruiter_email}. Skipping email.")
            return False
        
        try:
            # Create email content
            html_content = self._create_recruiter_test_completion_email_html(
                recruiter_name, candidate_name, candidate_email, 
                candidate_reference_number, job_role, completion_date,
                overall_score, analysis_report_url
            )
            text_content = self._create_recruiter_test_completion_email_text(
                recruiter_name, candidate_name, candidate_email, 
                candidate_reference_number, job_role, completion_date,
                overall_score, analysis_report_url
            )
            
            # Create subject
            subject = f"Test Completed - {candidate_name} - {job_role}"
            
            # Send email using SES
            return await self.send_email_ses(
                to_addresses=[recruiter_email],
                subject=subject,
                html_body=html_content,
                text_body=text_content
            )
            
        except Exception as e:
            logger.error(f"Error sending recruiter completion email to {recruiter_email}: {str(e)}", exc_info=True)
            return False
    
    def _get_system_design_analysis(self, candidate_id: str, db) -> Dict[str, Any]:
        """
        Fetch and format system design analysis from InterviewAnalysisTable.
        
        Args:
            candidate_id: UUID of the candidate
            db: Database session
            
        Returns:
            Dictionary with:
                - summary: System design summary
                - strengths: List of key strengths
                - improvements: List of areas for improvement
        """
        try:
            from models.interview_analysis_table import InterviewAnalysisTable
            
            interview_analysis = db.query(InterviewAnalysisTable).filter(
                InterviewAnalysisTable.candidate_id == candidate_id
            ).first()
            
            if not interview_analysis or not interview_analysis.system_design_analysis:
                return {
                    "summary": "System design assessment was not completed.",
                    "strengths": [],
                    "improvements": []
                }
            
            sd_analysis = interview_analysis.system_design_analysis
            
            # Extract data from system_design_analysis JSONB
            return {
                "summary": sd_analysis.get("summary", "System design assessment completed."),
                "strengths": sd_analysis.get("key_strengths", []),
                "improvements": sd_analysis.get("things_to_improve", [])
            }
        except Exception as e:
            logger.error(f"Error fetching system design analysis for candidate {candidate_id}: {str(e)}", exc_info=True)
            return {
                "summary": "System design assessment completed.",
                "strengths": [],
                "improvements": []
            }
    
    def _format_section_content(self, items, section_type: str, color: str) -> str:
        """
        Format section content with proper styling for email compatibility.
        
        Args:
            items: List of items to format or string for summary
            section_type: 'strengths', 'improvements', or 'summary'
            color: Color code for the icon/header
        
        Returns:
            Formatted HTML string
        """
        if not items:
            return ""
        
        # Icon mapping - using simple text characters instead of emojis for better email client support
        icons = {
            'strengths': '✓',
            'improvements': '!',
            'summary': '○'
        }
        
        # Title mapping
        titles = {
            'strengths': 'Strengths',
            'improvements': 'Areas for Improvement',
            'summary': 'Summary'
        }
        
        icon = icons.get(section_type, '●')
        title = titles.get(section_type, 'Details')
        
        # For summary (single text)
        if section_type == 'summary' and isinstance(items, str):
            return f'''
            <div style="margin-bottom: 20px; padding: 15px; background-color: #fefce8; border-left: 4px solid {color}; border-radius: 4px;">
                <table cellpadding="0" cellspacing="0" width="100%">
                    <tr>
                        <td style="width: 30px; vertical-align: top; padding-right: 10px;">
                            <span style="display: inline-block; width: 24px; height: 24px; line-height: 24px; text-align: center; background-color: {color}; color: white; border-radius: 50%; font-weight: bold; font-size: 14px;">{icon}</span>
                        </td>
                        <td style="vertical-align: top;">
                            <strong style="color: #333; font-size: 16px; display: block; margin-bottom: 8px;">{title}</strong>
                            <p style="margin: 0; color: #666; font-size: 14px; line-height: 1.6;">{items}</p>
                        </td>
                    </tr>
                </table>
            </div>
            '''
        
        # For lists
        if not isinstance(items, list) or not items:
            return ""
        
        list_items = "".join([f'<li style="margin-bottom: 6px; color: #666; line-height: 1.6;">{item}</li>' for item in items])
        
        bg_colors = {
            'strengths': '#f0fdf4',
            'improvements': '#fef2f2'
        }
        
        bg_color = bg_colors.get(section_type, '#f9fafb')
        
        return f'''
        <div style="margin-bottom: 20px; padding: 15px; background-color: {bg_color}; border-left: 4px solid {color}; border-radius: 4px;">
            <table cellpadding="0" cellspacing="0" width="100%">
                <tr>
                    <td style="width: 30px; vertical-align: top; padding-right: 10px;">
                        <span style="display: inline-block; width: 24px; height: 24px; line-height: 24px; text-align: center; background-color: {color}; color: white; border-radius: 50%; font-weight: bold; font-size: 14px;">{icon}</span>
                    </td>
                    <td style="vertical-align: top;">
                        <strong style="color: #333; font-size: 16px; display: block; margin-bottom: 10px;">{title}</strong>
                        <ul style="margin: 0; padding-left: 20px; list-style-type: disc;">
                            {list_items}
                        </ul>
                    </td>
                </tr>
            </table>
        </div>
        '''
    
    def _create_assessment_report_email_html(
        self,
        candidate_name: str,
        completion_date: datetime,
        mcq_analysis: Dict[str, Any],
        coding_analysis: Dict[str, Any],
        system_design_analysis: Dict[str, Any]
    ) -> str:
        """
        Create HTML email template for assessment report.
        
        Args:
            candidate_name: Candidate's name
            completion_date: Test completion date/time
            mcq_analysis: MCQ analysis dict with summary, strengths, improvements
            coding_analysis: Coding analysis dict with summary, strengths, improvements
            system_design_analysis: System design analysis dict with summary, strengths, improvements
            
        Returns:
            HTML email content
        """
        # Format completion date
        formatted_date = completion_date.strftime("%B %d, %Y at %I:%M %p")
        
        # Color scheme
        strength_color = '#10B981'  # Green
        improvement_color = '#FF6B35'  # Orange
        summary_color = '#FBBF24'  # Yellow
        
        # Format sections using helper
        mcq_strengths_html = self._format_section_content(
            mcq_analysis.get("strengths", []), 'strengths', strength_color
        ) if mcq_analysis.get("strengths") else ''
        
        mcq_improvements_html = self._format_section_content(
            mcq_analysis.get("improvements", []), 'improvements', improvement_color
        ) if mcq_analysis.get("improvements") else ''
        
        coding_strengths_html = self._format_section_content(
            coding_analysis.get("strengths", []), 'strengths', strength_color
        ) if coding_analysis.get("strengths") else ''
        
        coding_improvements_html = self._format_section_content(
            coding_analysis.get("improvements", []), 'improvements', improvement_color
        ) if coding_analysis.get("improvements") else ''
        
        sd_summary_html = self._format_section_content(
            system_design_analysis.get("summary", ""), 'summary', summary_color
        ) if system_design_analysis.get("summary") else ''
        
        sd_strengths_html = self._format_section_content(
            system_design_analysis.get("strengths", []), 'strengths', strength_color
        ) if system_design_analysis.get("strengths") else ''
        
        sd_improvements_html = self._format_section_content(
            system_design_analysis.get("improvements", []), 'improvements', improvement_color
        ) if system_design_analysis.get("improvements") else ''
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Interview Assessment Report</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
            
            <!-- Header -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <tr>
                    <td style="padding: 30px;">
                        <!-- Logo Section - Using table for better email client support -->
                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px;">
                            <tr>
                                <td style="width: 50%;">
                                    <table cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td style="padding-right: 8px; vertical-align: middle;">
                                                <span style="font-size: 24px; color: #FF6B35; font-weight: bold;">&lt;/&gt;</span>
                                            </td>
                                            <td style="vertical-align: middle;">
                                                <span style="font-size: 20px; font-weight: 600; color: #0069B4;">GAIA</span>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                                <td style="width: 50%; text-align: right;">
                                    <span style="font-size: 16px; font-weight: 600; color: #0069B4;">Grid Dynamics</span>
                                </td>
                            </tr>
                        </table>
                        
                        <!-- Title -->
                        <h1 style="color: #333; margin: 20px 0 10px 0; font-size: 28px; font-weight: 600;">Interview Assessment Report</h1>
                        <p style="color: #666; margin: 0; font-size: 14px;">Assessment completed on {formatted_date}</p>
                    </td>
                </tr>
            </table>
            
            <!-- Detailed Feedback by Section -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <tr>
                    <td style="padding: 30px;">
                        <h2 style="color: #333; margin-top: 0; font-size: 22px; font-weight: 600; margin-bottom: 25px;">Detailed Feedback by Section</h2>
                        
                        <!-- Section 1: MCQ -->
                        <div style="margin-bottom: 30px; padding-bottom: 25px; border-bottom: 2px solid #e5e5e5;">
                            <h3 style="color: #333; margin: 0 0 20px 0; font-size: 18px; font-weight: 600;">Section 1: Multiple Choice Assessment</h3>
                            {mcq_strengths_html}
                            {mcq_improvements_html}
                        </div>
                        
                        <!-- Section 2: Coding -->
                        <div style="margin-bottom: 30px; padding-bottom: 25px; border-bottom: 2px solid #e5e5e5;">
                            <h3 style="color: #333; margin: 0 0 20px 0; font-size: 18px; font-weight: 600;">Section 2: Coding Assessment</h3>
                            {coding_strengths_html}
                            {coding_improvements_html}
                        </div>
                        
                        <!-- Section 3: System Design -->
                        <div style="margin-bottom: 0;">
                            <h3 style="color: #333; margin: 0 0 20px 0; font-size: 18px; font-weight: 600;">Section 3: System Design Assessment</h3>
                            {sd_summary_html}
                            {sd_strengths_html}
                            {sd_improvements_html}
                        </div>
                    </td>
                </tr>
            </table>
            
            <!-- Next Steps -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <tr>
                    <td style="padding: 30px;">
                        <p style="color: #666; margin: 0 0 20px 0; font-size: 14px;">Thank you for completing the assessment. Here's what you can expect in the coming days regarding your application status.</p>
                        
                        <h3 style="color: #333; margin: 0 0 20px 0; font-size: 20px; font-weight: 600;">What Happens Next?</h3>
                        
                        <!-- Timeline Cards - Using table layout for email compatibility -->
                        <table width="100%" cellpadding="0" cellspacing="0">
                            <tr>
                                <td style="width: 48%; vertical-align: top; padding-bottom: 15px;">
                                    <div style="background-color: #f0f9ff; padding: 20px; border-radius: 8px; border-left: 4px solid #3B82F6;">
                                        <table cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td style="padding-right: 10px; vertical-align: top;">
                                                    <span style="font-size: 24px;">🕐</span>
                                                </td>
                                                <td style="vertical-align: top;">
                                                    <strong style="color: #333; font-size: 16px; display: block; margin-bottom: 8px;">Timeline</strong>
                                                    <p style="margin: 0; color: #666; font-size: 14px; line-height: 1.5;">Expect to hear from us within 3-5 business days</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </div>
                                </td>
                                <td style="width: 4%;"></td>
                                <td style="width: 48%; vertical-align: top; padding-bottom: 15px;">
                                    <div style="background-color: #fdf2f8; padding: 20px; border-radius: 8px; border-left: 4px solid #EC4899;">
                                        <table cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td style="padding-right: 10px; vertical-align: top;">
                                                    <span style="font-size: 24px;">✉️</span>
                                                </td>
                                                <td style="vertical-align: top;">
                                                    <strong style="color: #333; font-size: 16px; display: block; margin-bottom: 8px;">Contact Method</strong>
                                                    <p style="margin: 0; color: #666; font-size: 14px; line-height: 1.5;">Our HR team will email you with next steps</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <td style="width: 48%; vertical-align: top; padding-bottom: 15px;">
                                    <div style="background-color: #f0fdf4; padding: 20px; border-radius: 8px; border-left: 4px solid #10B981;">
                                        <table cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td style="padding-right: 10px; vertical-align: top;">
                                                    <span style="font-size: 24px;">📅</span>
                                                </td>
                                                <td style="vertical-align: top;">
                                                    <strong style="color: #333; font-size: 16px; display: block; margin-bottom: 8px;">Possible Next Round</strong>
                                                    <p style="margin: 0; color: #666; font-size: 14px; line-height: 1.5;">You may be invited for a non-technical interview with the hiring manager</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </div>
                                </td>
                                <td style="width: 4%;"></td>
                                <td style="width: 48%; vertical-align: top; padding-bottom: 15px;">
                                    <div style="background-color: #fff7ed; padding: 20px; border-radius: 8px; border-left: 4px solid #FF6B35;">
                                        <table cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td style="padding-right: 10px; vertical-align: top;">
                                                    <span style="font-size: 24px;">❓</span>
                                                </td>
                                                <td style="vertical-align: top;">
                                                    <strong style="color: #333; font-size: 16px; display: block; margin-bottom: 8px;">Questions?</strong>
                                                    <p style="margin: 0; color: #666; font-size: 14px; line-height: 1.5;">Contact us at <a href="mailto:hr@griddynamics.com" style="color: #0069B4; text-decoration: none;">hr@griddynamics.com</a></p>
                                                </td>
                                            </tr>
                                        </table>
                                    </div>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
            
            <!-- Footer -->
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td style="text-align: right; color: #999; font-size: 12px; padding: 20px 0;">
                        <p style="margin: 0;">Grid Dynamics © 2006-2025</p>
                    </td>
                </tr>
            </table>
            
        </body>
        </html>
        """
        return html_content
    
    def _create_assessment_report_email_text(
        self,
        candidate_name: str,
        completion_date: datetime,
        mcq_analysis: Dict[str, Any],
        coding_analysis: Dict[str, Any],
        system_design_analysis: Dict[str, Any]
    ) -> str:
        """
        Create plain text email template for assessment report.
        
        Args:
            candidate_name: Candidate's name
            completion_date: Test completion date/time
            mcq_analysis: MCQ analysis dict with summary, strengths, improvements
            coding_analysis: Coding analysis dict with summary, strengths, improvements
            system_design_analysis: System design analysis dict with summary, strengths, improvements
            
        Returns:
            Plain text email content
        """
        formatted_date = completion_date.strftime("%B %d, %Y at %I:%M %p")
        
        text_content = f"""
Interview Assessment Report - GAIA

Assessment completed on {formatted_date}

DETAILED FEEDBACK BY SECTION

Section 1: Multiple Choice Assessment
"""
        
        if mcq_analysis.get("strengths"):
            text_content += "\nStrengths:\n"
            for strength in mcq_analysis.get("strengths", []):
                text_content += f"- {strength}\n"
        
        if mcq_analysis.get("improvements"):
            text_content += "\nAreas for Improvement:\n"
            for improvement in mcq_analysis.get("improvements", []):
                text_content += f"- {improvement}\n"
        
        text_content += "\nSection 2: Coding Assessment\n"
        
        if coding_analysis.get("strengths"):
            text_content += "\nStrengths:\n"
            for strength in coding_analysis.get("strengths", []):
                text_content += f"- {strength}\n"
        
        if coding_analysis.get("improvements"):
            text_content += "\nAreas for Improvement:\n"
            for improvement in coding_analysis.get("improvements", []):
                text_content += f"- {improvement}\n"
        
        text_content += "\nSection 3: System Design Assessment\n"
        
        if system_design_analysis.get("summary"):
            text_content += f"\nSummary: {system_design_analysis.get('summary')}\n"
        
        if system_design_analysis.get("strengths"):
            text_content += "\nStrengths:\n"
            for strength in system_design_analysis.get("strengths", []):
                text_content += f"- {strength}\n"
        
        if system_design_analysis.get("improvements"):
            text_content += "\nAreas for Improvement:\n"
            for improvement in system_design_analysis.get("improvements", []):
                text_content += f"- {improvement}\n"
        
        text_content += """
NEXT STEPS

Thank you for completing the assessment. Here's what you can expect in the coming days regarding your application status.

What Happens Next?

Timeline: Expect to hear from us within 3-5 business days
Contact Method: Our HR team will email you with next steps
Possible Next Round: You may be invited for a non-technical interview with the hiring manager
Questions?: Contact us at hr@griddynamics.com

---
Grid Dynamics © 2006-2025
        """
        
        return text_content.strip()
    
    def _are_all_analyses_ready(self, candidate_id: str, db) -> bool:
        """
        Check if all required analyses are present in InterviewAnalysisTable.
        
        Args:
            candidate_id: UUID of the candidate
            db: Database session
            
        Returns:
            True if all required analyses are present, False otherwise
        """
        try:
            from models.interview_analysis_table import InterviewAnalysisTable
            
            interview_analysis = db.query(InterviewAnalysisTable).filter(
                InterviewAnalysisTable.candidate_id == candidate_id
            ).first()
            
            if not interview_analysis:
                logger.info(f"Interview analysis record not found for candidate {candidate_id}")
                return False
            
            # Check if all required analyses are present
            mcq_ready = interview_analysis.mcq_analysis is not None
            coding_ready = interview_analysis.coding_analysis is not None
            system_design_ready = interview_analysis.system_design_analysis is not None
            
            if not mcq_ready:
                logger.info(f"MCQ analysis not ready for candidate {candidate_id}")
            if not coding_ready:
                logger.info(f"Coding analysis not ready for candidate {candidate_id}")
            if not system_design_ready:
                logger.info(f"System design analysis not ready for candidate {candidate_id}")
            
            all_ready = mcq_ready and coding_ready and system_design_ready
            
            if all_ready:
                logger.info(f"All analyses are ready for candidate {candidate_id}")
            else:
                logger.info(f"Not all analyses are ready for candidate {candidate_id} (MCQ: {mcq_ready}, Coding: {coding_ready}, System Design: {system_design_ready})")
            
            return all_ready
            
        except Exception as e:
            logger.error(f"Error checking if analyses are ready for candidate {candidate_id}: {str(e)}", exc_info=True)
            return False
    
    async def send_assessment_report_email(
        self,
        candidate_id: str,
        candidate_email: str,
        candidate_name: str,
        completion_date: datetime,
        db
    ) -> bool:
        """
        Send assessment report email to candidate after test completion.
        Only sends email if all required analyses (MCQ, Coding, System Design) are ready.
        
        Args:
            candidate_id: UUID of the candidate
            candidate_email: Candidate's email address
            candidate_name: Candidate's name
            completion_date: Test completion date/time
            db: Database session
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Check if email is enabled
        if not self.enabled:
            logger.info(f"Email sending is disabled. Skipping assessment report email to {candidate_email}")
            return False
        
        # Validate email
        if not self._is_valid_email(candidate_email):
            logger.warning(f"Invalid or placeholder email address: {candidate_email}. Skipping email.")
            return False
        
        # Check if all analyses are ready before proceeding
        if not self._are_all_analyses_ready(candidate_id, db):
            logger.warning(f"Not all analyses are ready for candidate {candidate_id}. Email will not be sent. Analyses must be completed first.")
            return False
        
        try:
            # Generate analyses (these will use data from InterviewAnalysisTable)
            from services.mcq_analysis_service import generate_mcq_analysis
            from services.coding_analysis_service import generate_coding_analysis
            
            logger.info(f"[DATA_SOURCE] 📊 Fetching analysis data from POSTGRESQL (InterviewAnalysisTable) for candidate {candidate_id}")
            logger.info(f"[DATA_SOURCE] 🔄 Generating analyses for candidate {candidate_id} (using data from POSTGRESQL)")
            
            # Generate MCQ analysis (reads from InterviewAnalysisTable.mcq_analysis)
            logger.info(f"[DATA_SOURCE] 📥 Generating MCQ analysis from POSTGRESQL data for candidate {candidate_id}")
            mcq_analysis = await generate_mcq_analysis(candidate_id, db)
            
            # Generate Coding analysis (reads from InterviewAnalysisTable.coding_analysis)
            logger.info(f"[DATA_SOURCE] 📥 Generating coding analysis from POSTGRESQL data for candidate {candidate_id}")
            coding_analysis = await generate_coding_analysis(candidate_id, db)
            
            # Fetch System Design analysis (reads from InterviewAnalysisTable.system_design_analysis)
            logger.info(f"[DATA_SOURCE] 📥 Fetching system design analysis from POSTGRESQL for candidate {candidate_id}")
            system_design_analysis = self._get_system_design_analysis(candidate_id, db)
            
            # Create email content
            html_content = self._create_assessment_report_email_html(
                candidate_name, completion_date, mcq_analysis, coding_analysis, system_design_analysis
            )
            text_content = self._create_assessment_report_email_text(
                candidate_name, completion_date, mcq_analysis, coding_analysis, system_design_analysis
            )
            
            # Send email using SES
            return await self.send_email_ses(
                to_addresses=[candidate_email],
                subject="Interview Assessment Report - TechInterview Platform",
                html_body=html_content,
                text_body=text_content
            )
            
        except Exception as e:
            logger.error(f"Error sending assessment report email to {candidate_email}: {str(e)}", exc_info=True)
            return False
    
    async def try_send_assessment_report_email_if_ready(
        self,
        candidate_id: str,
        db
    ) -> bool:
        """
        Attempt to send assessment report email if all analyses are ready.
        This can be called after any analysis update to check if email should be sent.
        
        Args:
            candidate_id: UUID of the candidate
            db: Database session
            
        Returns:
            True if email was sent successfully, False otherwise (including if not ready)
        """
        try:
            from models.candidate import Candidate
            
            # Get candidate info
            candidate = db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()
            
            if not candidate:
                logger.warning(f"Candidate {candidate_id} not found")
                return False
            
            # Only send if test is completed
            if candidate.status != 'completed':
                logger.info(f"Candidate {candidate_id} test not completed yet (status: {candidate.status})")
                return False
            
            # Get completion date from test session
            completion_date = datetime.utcnow()
            if candidate.test_session and candidate.test_session.test_completed_at:
                completion_date = candidate.test_session.test_completed_at
            
            # Try to send email (will check if all analyses are ready internally)
            return await self.send_assessment_report_email(
                candidate_id=candidate_id,
                candidate_email=candidate.email_id,
                candidate_name=candidate.name,
                completion_date=completion_date,
                db=db
            )
            
        except Exception as e:
            logger.error(f"Error in try_send_assessment_report_email_if_ready for candidate {candidate_id}: {str(e)}", exc_info=True)
            return False


# Create singleton instance - handle import errors gracefully
try:
    email_service = EmailService()
except Exception as e:
    logger.error(f"Failed to create email service singleton: {e}. Email functionality will be disabled.")
    # Create a dummy service that does nothing
    class DummyEmailService:
        enabled = False
        async def send_invitation_email(self, *args, **kwargs):
            return False
        async def send_scheduling_invitation_email(self, *args, **kwargs):
            return False
        async def send_test_invitation_email(self, *args, **kwargs):
            return False
        async def send_assessment_report_email(self, *args, **kwargs):
            return False
        async def send_assessment_report_email(self, *args, **kwargs):
            return False
    email_service = DummyEmailService()


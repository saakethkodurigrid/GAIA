"""
Email service for sending invitation emails to candidates.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
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
            # Import pydantic SecretStr first to ensure it's available
            from pydantic import SecretStr  # noqa: F401
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
                <div style="text-align: center; margin-bottom: 20px;">
                    <h1 style="color: #0069B4; margin: 0; font-size: 28px;">TechInterview Platform</h1>
                </div>
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
                    </ul>
                </div>
                
                <p style="margin-top: 30px;">We look forward to speaking with you!</p>
                
                <p>Best regards,<br>
                <strong>TechInterview Platform Team</strong></p>
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
Interview Invitation - TechInterview Platform

Dear {candidate_name},

Congratulations! We are pleased to invite you to proceed with the interview process for the position of {job_role}.

We were impressed with your qualifications and would like to move forward with the next steps. Please use the link below to schedule your interview:

{invitation_link}

What to expect:
- Select a convenient date and time for your interview
- Complete the interview process which includes multiple choice questions, Coding, and System Design assessments
- You'll need to sign in with your Google account (please use the account associated with the email address you provided to the recruiting team) to proceed

We look forward to speaking with you!

Best regards,
TechInterview Platform Team

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
        
        # Check if email configuration is set
        if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD or not settings.MAIL_FROM:
            logger.warning("Email configuration is incomplete. Skipping email.")
            return False
        
        try:
            # Ensure email service is initialized
            self._ensure_initialized()
            _, MessageSchema, _ = _lazy_import_fastapi_mail()
            
            # Generate invitation link
            invitation_link = self._generate_invitation_link(candidate_id)
            
            # Create email content
            html_content = self._create_invitation_email_html(
                candidate_name, job_role, resume_score, invitation_link
            )
            text_content = self._create_invitation_email_text(
                candidate_name, job_role, resume_score, invitation_link
            )
            
            # Create message
            message = MessageSchema(
                subject=f"Interview Invitation - {job_role}",
                recipients=[candidate_email],
                body=html_content,
                subtype="html",
                # Include plain text alternative
                alternatives=[{"content": text_content, "subtype": "plain"}]
            )
            
            # Send email
            await self.fastmail.send_message(message)
            logger.info(f"Successfully sent invitation email to {candidate_email} for candidate {candidate_id}")
            return True
            
        except Exception as e:
            # Lazy import errors if needed
            ConnectionErrors, SMTPAuthenticationError = _lazy_import_errors()
            if isinstance(e, (ConnectionErrors, SMTPAuthenticationError)):
                error_msg = str(e)
                # Check if it's a Google app-specific password error
                if 'Application-specific password required' in error_msg or '534' in error_msg:
                    logger.error(
                        f"Failed to send invitation email to {candidate_email}: "
                        "Google requires an application-specific password because 2FA is enabled. "
                        "Please generate an app-specific password from your Google Account settings "
                        "(https://myaccount.google.com/apppasswords) and use it as MAIL_PASSWORD in your environment variables."
                    )
                else:
                    logger.error(f"Failed to send invitation email to {candidate_email}: {error_msg}", exc_info=True)
                return False
            else:
                # Re-raise if it's not a connection/auth error
                raise
    
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
                <div style="text-align: center; margin-bottom: 20px;">
                    <h1 style="color: #0069B4; margin: 0; font-size: 28px;">TechInterview Platform</h1>
                </div>
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
                    </ul>
                </div>
                
                <p style="margin-top: 30px;">Good luck with your assessment!</p>
                
                <p>Best regards,<br>
                <strong>TechInterview Platform Team</strong></p>
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
Test Scheduled - Ready to Begin - TechInterview Platform

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

Good luck with your assessment!

Best regards,
TechInterview Platform Team

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
        
        # Check if email configuration is set
        if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD or not settings.MAIL_FROM:
            logger.warning("Email configuration is incomplete. Skipping email.")
            return False
        
        try:
            # Ensure email service is initialized
            self._ensure_initialized()
            _, MessageSchema, _ = _lazy_import_fastapi_mail()
            
            # Generate scheduling invitation link
            invitation_link = self._generate_invitation_link(candidate_id, link_type="scheduling")
            
            # Create email content (pass None for resume_score to not display it)
            html_content = self._create_invitation_email_html(
                candidate_name, job_role, None, invitation_link
            )
            text_content = self._create_invitation_email_text(
                candidate_name, job_role, None, invitation_link
            )
            
            # Create message
            message = MessageSchema(
                subject=f"Interview Invitation - {job_role}",
                recipients=[candidate_email],
                body=html_content,
                subtype="html",
                # Include plain text alternative
                alternatives=[{"content": text_content, "subtype": "plain"}]
            )
            
            # Send email
            await self.fastmail.send_message(message)
            logger.info(f"Successfully sent scheduling invitation email to {candidate_email} for candidate {candidate_id}")
            return True
            
        except Exception as e:
            # Lazy import errors if needed
            ConnectionErrors, SMTPAuthenticationError = _lazy_import_errors()
            if isinstance(e, (ConnectionErrors, SMTPAuthenticationError)):
                error_msg = str(e)
                # Check if it's a Google app-specific password error
                if 'Application-specific password required' in error_msg or '534' in error_msg:
                    logger.error(
                        f"Failed to send scheduling invitation email to {candidate_email}: "
                        "Google requires an application-specific password because 2FA is enabled. "
                        "Please generate an app-specific password from your Google Account settings "
                        "(https://myaccount.google.com/apppasswords) and use it as MAIL_PASSWORD in your environment variables."
                    )
                else:
                    logger.error(f"Failed to send scheduling invitation email to {candidate_email}: {error_msg}", exc_info=True)
                return False
            else:
                # Re-raise if it's not a connection/auth error
                raise
    
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
        
        # Check if email configuration is set
        if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD or not settings.MAIL_FROM:
            logger.warning("Email configuration is incomplete. Skipping email.")
            return False
        
        try:
            # Ensure email service is initialized
            self._ensure_initialized()
            _, MessageSchema, _ = _lazy_import_fastapi_mail()
            
            # Generate test invitation link
            invitation_link = self._generate_invitation_link(candidate_id, link_type="test")
            
            # Create email content
            html_content = self._create_test_invitation_email_html(
                candidate_name, job_role, scheduled_date, invitation_link
            )
            text_content = self._create_test_invitation_email_text(
                candidate_name, job_role, scheduled_date, invitation_link
            )
            
            # Create message
            formatted_date = scheduled_date.strftime("%B %d, %Y at %I:%M %p")
            message = MessageSchema(
                subject=f"Test Scheduled - {job_role} - {formatted_date}",
                recipients=[candidate_email],
                body=html_content,
                subtype="html",
                # Include plain text alternative
                alternatives=[{"content": text_content, "subtype": "plain"}]
            )
            
            # Send email
            await self.fastmail.send_message(message)
            logger.info(f"Successfully sent test invitation email to {candidate_email} for candidate {candidate_id}")
            return True
            
        except Exception as e:
            # Lazy import errors if needed
            ConnectionErrors, SMTPAuthenticationError = _lazy_import_errors()
            if isinstance(e, (ConnectionErrors, SMTPAuthenticationError)):
                error_msg = str(e)
                # Check if it's a Google app-specific password error
                if 'Application-specific password required' in error_msg or '534' in error_msg:
                    logger.error(
                        f"Failed to send test invitation email to {candidate_email}: "
                        "Google requires an application-specific password because 2FA is enabled. "
                        "Please generate an app-specific password from your Google Account settings "
                        "(https://myaccount.google.com/apppasswords) and use it as MAIL_PASSWORD in your environment variables."
                    )
                else:
                    logger.error(f"Failed to send test invitation email to {candidate_email}: {error_msg}", exc_info=True)
                return False
            else:
                # Re-raise if it's not a connection/auth error
                raise
    
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
        
        # Format strengths and improvements lists
        def format_list(items):
            if not items:
                return ""
            return "".join([f'<li>{item}</li>' for item in items])
        
        mcq_strengths = format_list(mcq_analysis.get("strengths", []))
        mcq_improvements = format_list(mcq_analysis.get("improvements", []))
        coding_strengths = format_list(coding_analysis.get("strengths", []))
        coding_improvements = format_list(coding_analysis.get("improvements", []))
        sd_summary = system_design_analysis.get("summary", "")
        sd_strengths = format_list(system_design_analysis.get("strengths", []))
        sd_improvements = format_list(system_design_analysis.get("improvements", []))
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
            <!-- Header -->
            <div style="background-color: #ffffff; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 24px; color: #FF6B35;">&lt;/&gt;</span>
                        <span style="font-size: 20px; font-weight: 600; color: #333;">TechInterview</span>
                    </div>
                    <div style="font-size: 16px; font-weight: 600; color: #0069B4;">Grid Dynamics</div>
                </div>
                
                <h1 style="color: #333; margin: 20px 0 10px 0; font-size: 28px; font-weight: 600;">Interview Assessment Report</h1>
                <p style="color: #666; margin: 0; font-size: 14px;">Assessment completed on {formatted_date}</p>
            </div>
            
            <!-- Detailed Feedback by Section -->
            <div style="background-color: #ffffff; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #333; margin-top: 0; font-size: 22px; font-weight: 600; margin-bottom: 25px;">Detailed Feedback by Section</h2>
                
                <!-- Section 1: Multiple Choice Assessment -->
                <div style="margin-bottom: 30px; padding-bottom: 25px; border-bottom: 1px solid #e5e5e5;">
                    <h3 style="color: #333; margin: 0 0 15px 0; font-size: 18px; font-weight: 600;">Section 1: Multiple Choice Assessment</h3>
                    
                    {f'<div style="margin-bottom: 15px;"><div style="display: flex; align-items: start; gap: 10px; margin-bottom: 8px;"><span style="color: #10B981; font-size: 18px;">🛡️</span><strong style="color: #333;">Strengths</strong></div><ul style="margin: 0; padding-left: 30px; color: #666;">{mcq_strengths}</ul></div>' if mcq_strengths else ''}
                    
                    {f'<div><div style="display: flex; align-items: start; gap: 10px; margin-bottom: 8px;"><span style="color: #FF6B35; font-size: 18px;">⚠️</span><strong style="color: #333;">Areas for Improvement</strong></div><ul style="margin: 0; padding-left: 30px; color: #666;">{mcq_improvements}</ul></div>' if mcq_improvements else ''}
                </div>
                
                <!-- Section 2: Coding Assessment -->
                <div style="margin-bottom: 30px; padding-bottom: 25px; border-bottom: 1px solid #e5e5e5;">
                    <h3 style="color: #333; margin: 0 0 15px 0; font-size: 18px; font-weight: 600;">Section 2: Coding Assessment</h3>
                    
                    {f'<div style="margin-bottom: 15px;"><div style="display: flex; align-items: start; gap: 10px; margin-bottom: 8px;"><span style="color: #10B981; font-size: 18px;">🛡️</span><strong style="color: #333;">Strengths</strong></div><ul style="margin: 0; padding-left: 30px; color: #666;">{coding_strengths}</ul></div>' if coding_strengths else ''}
                    
                    {f'<div><div style="display: flex; align-items: start; gap: 10px; margin-bottom: 8px;"><span style="color: #FF6B35; font-size: 18px;">⚠️</span><strong style="color: #333;">Areas for Improvement</strong></div><ul style="margin: 0; padding-left: 30px; color: #666;">{coding_improvements}</ul></div>' if coding_improvements else ''}
                </div>
                
                <!-- Section 3: System Design Assessment -->
                <div>
                    <h3 style="color: #333; margin: 0 0 15px 0; font-size: 18px; font-weight: 600;">Section 3: System Design Assessment</h3>
                    
                    {f'<div style="margin-bottom: 15px;"><div style="display: flex; align-items: start; gap: 10px; margin-bottom: 8px;"><span style="color: #FBBF24; font-size: 18px;">⭕</span><strong style="color: #333;">Summary</strong></div><p style="margin: 0; padding-left: 30px; color: #666;">{sd_summary}</p></div>' if sd_summary else ''}
                    
                    {f'<div style="margin-bottom: 15px;"><div style="display: flex; align-items: start; gap: 10px; margin-bottom: 8px;"><span style="color: #10B981; font-size: 18px;">🛡️</span><strong style="color: #333;">Strengths</strong></div><ul style="margin: 0; padding-left: 30px; color: #666;">{sd_strengths}</ul></div>' if sd_strengths else ''}
                    
                    {f'<div><div style="display: flex; align-items: start; gap: 10px; margin-bottom: 8px;"><span style="color: #FF6B35; font-size: 18px;">⚠️</span><strong style="color: #333;">Areas for Improvement</strong></div><ul style="margin: 0; padding-left: 30px; color: #666;">{sd_improvements}</ul></div>' if sd_improvements else ''}
                </div>
            </div>
            
            <!-- Next Steps -->
            <div style="background-color: #ffffff; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <p style="color: #666; margin: 0 0 20px 0; font-size: 14px;">Thank you for completing the assessment. Here's what you can expect in the coming days regarding your application status.</p>
                
                <h3 style="color: #333; margin: 0 0 20px 0; font-size: 20px; font-weight: 600;">What Happens Next?</h3>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                    <!-- Timeline Card -->
                    <div style="background-color: #f0f9ff; padding: 20px; border-radius: 8px; border-left: 4px solid #3B82F6;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                            <span style="font-size: 24px;">🕐</span>
                            <strong style="color: #333; font-size: 16px;">Timeline</strong>
                        </div>
                        <p style="margin: 0; color: #666; font-size: 14px;">Expect to hear from us within 3-5 business days</p>
                    </div>
                    
                    <!-- Contact Method Card -->
                    <div style="background-color: #fdf2f8; padding: 20px; border-radius: 8px; border-left: 4px solid #EC4899;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                            <span style="font-size: 24px;">✉️</span>
                            <strong style="color: #333; font-size: 16px;">Contact Method</strong>
                        </div>
                        <p style="margin: 0; color: #666; font-size: 14px;">Our HR team will email you with next steps</p>
                    </div>
                    
                    <!-- Possible Next Round Card -->
                    <div style="background-color: #f0fdf4; padding: 20px; border-radius: 8px; border-left: 4px solid #10B981;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                            <span style="font-size: 24px;">📅</span>
                            <strong style="color: #333; font-size: 16px;">Possible Next Round</strong>
                        </div>
                        <p style="margin: 0; color: #666; font-size: 14px;">You may be invited for a non-technical interview with the hiring manager</p>
                    </div>
                    
                    <!-- Questions Card -->
                    <div style="background-color: #fff7ed; padding: 20px; border-radius: 8px; border-left: 4px solid #FF6B35;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                            <span style="font-size: 24px;">❓</span>
                            <strong style="color: #333; font-size: 16px;">Questions?</strong>
                        </div>
                        <p style="margin: 0; color: #666; font-size: 14px;">Contact us at hr@griddynamics.com</p>
                    </div>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="text-align: right; color: #999; font-size: 12px; padding: 20px 0;">
                <p style="margin: 0;">Grid Dynamics © 2006-2025</p>
            </div>
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
Interview Assessment Report - TechInterview Platform

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
        
        # Check if email configuration is set
        if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD or not settings.MAIL_FROM:
            logger.warning("Email configuration is incomplete. Skipping email.")
            return False
        
        # Check if all analyses are ready before proceeding
        if not self._are_all_analyses_ready(candidate_id, db):
            logger.warning(f"Not all analyses are ready for candidate {candidate_id}. Email will not be sent. Analyses must be completed first.")
            return False
        
        try:
            # Generate analyses (these will use data from InterviewAnalysisTable)
            from services.mcq_analysis_service import generate_mcq_analysis
            from services.coding_analysis_service import generate_coding_analysis
            
            logger.info(f"Generating analyses for candidate {candidate_id}")
            
            # Generate MCQ analysis
            mcq_analysis = await generate_mcq_analysis(candidate_id, db)
            
            # Generate Coding analysis
            coding_analysis = await generate_coding_analysis(candidate_id, db)
            
            # Fetch System Design analysis
            system_design_analysis = self._get_system_design_analysis(candidate_id, db)
            
            # Ensure email service is initialized
            self._ensure_initialized()
            _, MessageSchema, _ = _lazy_import_fastapi_mail()
            
            # Create email content
            html_content = self._create_assessment_report_email_html(
                candidate_name, completion_date, mcq_analysis, coding_analysis, system_design_analysis
            )
            text_content = self._create_assessment_report_email_text(
                candidate_name, completion_date, mcq_analysis, coding_analysis, system_design_analysis
            )
            
            # Create message
            message = MessageSchema(
                subject="Interview Assessment Report - TechInterview Platform",
                recipients=[candidate_email],
                body=html_content,
                subtype="html",
                # Include plain text alternative
                alternatives=[{"content": text_content, "subtype": "plain"}]
            )
            
            # Send email
            await self.fastmail.send_message(message)
            logger.info(f"Successfully sent assessment report email to {candidate_email} for candidate {candidate_id}")
            return True
            
        except Exception as e:
            # Lazy import errors if needed
            ConnectionErrors, SMTPAuthenticationError = _lazy_import_errors()
            if isinstance(e, (ConnectionErrors, SMTPAuthenticationError)):
                error_msg = str(e)
                logger.error(f"Failed to send assessment report email to {candidate_email}: {error_msg}", exc_info=True)
                return False
            else:
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
    email_service = DummyEmailService()


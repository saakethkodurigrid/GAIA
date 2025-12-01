"""
Email service for sending invitation emails to candidates.
"""
import logging
from typing import Optional
from datetime import datetime
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails to candidates."""
    
    def __init__(self):
        """Initialize email service with configuration."""
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
        self.enabled = settings.EMAIL_ENABLED
    
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
        score_section = ""
        if resume_score is not None:
            score_section = f"""
            <div style="margin: 20px 0; padding: 15px; background-color: #f0f9ff; border-left: 4px solid #0069B4; border-radius: 4px;">
                <p style="margin: 0; color: #1e40af; font-weight: 600;">Your Resume Score: {resume_score:.1f}/100</p>
            </div>
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
                
                {score_section}
                
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
                        <li>Complete the interview process which includes MCQ, Coding, and System Design assessments</li>
                        <li>You'll need to sign in with your Google account to proceed</li>
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
        score_text = ""
        if resume_score is not None:
            score_text = f"\nYour Resume Score: {resume_score:.1f}/100\n"
        
        text_content = f"""
Interview Invitation - TechInterview Platform

Dear {candidate_name},

Congratulations! We are pleased to invite you to proceed with the interview process for the position of {job_role}.
{score_text}
We were impressed with your qualifications and would like to move forward with the next steps. Please use the link below to schedule your interview:

{invitation_link}

What to expect:
- Select a convenient date and time for your interview
- Complete the interview process which includes MCQ, Coding, and System Design assessments
- You'll need to sign in with your Google account to proceed

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
            logger.error(f"Failed to send invitation email to {candidate_email}: {str(e)}", exc_info=True)
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
                        <li>The test includes MCQ, Coding, and System Design assessments</li>
                        <li>You'll need to sign in with your Google account to proceed</li>
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
- The test includes MCQ, Coding, and System Design assessments
- You'll need to sign in with your Google account to proceed

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
            # Generate scheduling invitation link
            invitation_link = self._generate_invitation_link(candidate_id, link_type="scheduling")
            
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
            logger.info(f"Successfully sent scheduling invitation email to {candidate_email} for candidate {candidate_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send scheduling invitation email to {candidate_email}: {str(e)}", exc_info=True)
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
        
        # Check if email configuration is set
        if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD or not settings.MAIL_FROM:
            logger.warning("Email configuration is incomplete. Skipping email.")
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
            logger.error(f"Failed to send test invitation email to {candidate_email}: {str(e)}", exc_info=True)
            return False


# Create singleton instance
email_service = EmailService()


"""
Google Calendar service for creating calendar invites using OAuth.
Uses shared calendar account credentials stored in system_config table.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.config import settings

logger = logging.getLogger(__name__)

# Lazy imports for Google Calendar
_google_calendar_imported = False
_Credentials = None
_build = None


def _lazy_import_google_calendar():
    """Lazy import Google Calendar dependencies."""
    global _google_calendar_imported, _Credentials, _build
    if not _google_calendar_imported:
        try:
            from google.oauth2.credentials import Credentials as Creds
            from googleapiclient.discovery import build as gb
            _Credentials = Creds
            _build = gb
            _google_calendar_imported = True
        except ImportError as e:
            logger.error(f"Failed to import Google Calendar dependencies: {e}")
            raise
    return _Credentials, _build


class CalendarService:
    """Service for managing Google Calendar invitations using OAuth."""
    
    def __init__(self):
        """Initialize calendar service with configuration."""
        self.enabled = settings.GOOGLE_CALENDAR_ENABLED
        self.service = None
        self.credentials = None
        self._initialized = False
        
    def _get_oauth_credentials(self, db):
        """
        Get OAuth credentials for shared calendar account from database.
        
        Args:
            db: Database session
            
        Returns:
            OAuth credentials or None if not authorized
            
        Raises:
            Exception: If credentials cannot be loaded or refreshed
        """
        from models.system_config import SystemConfig
        
        CredentialsClass, _ = _lazy_import_google_calendar()
        
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == 'calendar_oauth_credentials'
        ).first()
        
        if not config:
            logger.warning("Shared calendar account not authorized. Calendar invites will not be sent.")
            return None
        
        try:
            creds_data = json.loads(config.config_value)
            
            credentials = CredentialsClass(
                token=creds_data['token'],
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=creds_data.get('client_id', settings.GOOGLE_CLIENT_ID),
                client_secret=creds_data.get('client_secret', settings.GOOGLE_CLIENT_SECRET),
                scopes=creds_data.get('scopes', [
                    'https://www.googleapis.com/auth/calendar',
                    'https://www.googleapis.com/auth/calendar.events'
                ])
            )
            
            # Refresh token if expired
            if credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    
                    # Update stored token in database
                    creds_data['token'] = credentials.token
                    config.config_value = json.dumps(creds_data)
                    db.commit()
                    logger.info("Refreshed expired calendar OAuth token")
                except Exception as e:
                    logger.error(f"Failed to refresh calendar OAuth token: {e}")
                    # Token refresh failed - might need re-authorization
                    return None
            
            return credentials
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse calendar OAuth credentials: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load calendar OAuth credentials: {e}", exc_info=True)
            return None
    
    def _ensure_initialized(self, db):
        """
        Lazy initialization of Google Calendar service.
        
        Args:
            db: Database session (required for OAuth token lookup)
        """
        if not self._initialized:
            try:
                _, build_module = _lazy_import_google_calendar()
                self.credentials = self._get_oauth_credentials(db)
                
                if not self.credentials:
                    raise ValueError("Calendar account not authorized. Please authorize calendar access first.")
                
                self.service = build_module('calendar', 'v3', credentials=self.credentials)
                self._initialized = True
                logger.info("Google Calendar service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Google Calendar service: {e}")
                self.enabled = False
                raise
    
    def _format_datetime_for_calendar(self, dt: datetime, timezone: str = None) -> Dict[str, str]:
        """
        Format datetime for Google Calendar API.
        
        Args:
            dt: Datetime object
            timezone: Timezone string (e.g., 'Asia/Kolkata')
            
        Returns:
            Dictionary with dateTime and timeZone
        """
        if timezone is None:
            timezone = settings.CALENDAR_TIMEZONE
        
        return {
            'dateTime': dt.isoformat(),
            'timeZone': timezone
        }
    
    async def create_candidate_calendar_event(
        self,
        candidate_email: str,
        candidate_name: str,
        job_role: str,
        test_link: str,
        scheduled_date: datetime,
        db,  # Database session required for OAuth token lookup
        test_duration_hours: int = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a calendar event for the candidate with test invitation.
        Uses shared OAuth calendar account.
        
        Args:
            candidate_email: Candidate's email address
            candidate_name: Candidate's name
            job_role: Job role/title
            test_link: URL for the test
            scheduled_date: Test start date/time
            db: Database session (required for OAuth token lookup)
            test_duration_hours: Test duration in hours (default from settings)
            
        Returns:
            Created event details or None if failed
        """
        if not self.enabled:
            logger.info("Google Calendar is disabled. Skipping calendar invite for candidate.")
            return None
        
        try:
            # Ensure service is initialized (requires db session)
            self._ensure_initialized(db)
            
            # Calculate end time
            if test_duration_hours is None:
                test_duration_hours = settings.TEST_DURATION_HOURS
            end_date = scheduled_date + timedelta(hours=test_duration_hours)
            
            # Format dates
            start_time = self._format_datetime_for_calendar(scheduled_date)
            end_time = self._format_datetime_for_calendar(end_date)
            
            # Create event description (similar to email template)
            formatted_date = scheduled_date.strftime("%B %d, %Y at %I:%M %p")
            description = f"""Technical Interview - {job_role}

Dear {candidate_name},

Your technical interview has been scheduled for {formatted_date} (IST).

Important Instructions:
• Please be ready 5 minutes before the scheduled time
• Ensure you have a stable internet connection
• The test includes multiple choice questions, Coding, and System Design assessments
• You'll need to sign in with your Google account to proceed

Test Link: {test_link}

Good luck with your assessment!

Best regards,
TechInterview Platform Team
"""
            
            # Create event with proper structure for calendar invites
            event = {
                'summary': f'Technical Interview - {job_role}',
                'location': test_link,
                'description': description,
                'start': start_time,
                'end': end_time,
                'attendees': [
                    {
                        'email': candidate_email,
                        'responseStatus': 'needsAction',  # Explicitly set for RSVP
                        'optional': False
                    }
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': settings.CALENDAR_REMINDER_MINUTES},
                        {'method': 'email', 'minutes': 1440},  # 24 hours before
                    ],
                },
                'guestsCanInviteOthers': False,
                'guestsCanModify': False,
                'guestsCanSeeOtherGuests': True,
                'colorId': '9',  # Blue color for better visibility
            }
            
            # Insert event with proper notification settings
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all',  # Send to all attendees
                sendNotifications=True,  # CRITICAL: Enable notifications for proper calendar invites
                conferenceDataVersion=0
            ).execute()
            
            logger.info(
                f"Successfully created calendar event for candidate {candidate_email}. "
                f"Event ID: {created_event.get('id')}, "
                f"Link: {created_event.get('htmlLink')}"
            )
            
            return {
                'event_id': created_event.get('id'),
                'event_link': created_event.get('htmlLink'),
                'status': 'created'
            }
            
        except ValueError as e:
            # Calendar not authorized
            logger.warning(f"Calendar not authorized: {e}")
            return None
        except HttpError as e:
            logger.error(f"Google Calendar API error for candidate {candidate_email}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create calendar event for candidate {candidate_email}: {e}", exc_info=True)
            return None
    
    async def create_recruiter_calendar_event(
        self,
        recruiter_email: str,
        recruiter_name: str,
        candidate_name: str,
        candidate_email: str,
        candidate_reference_number: Optional[str],
        job_role: str,
        scheduled_date: datetime,
        db,  # Database session required for OAuth token lookup
        test_duration_hours: int = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a calendar event for the recruiter (notification, no test link).
        Uses shared OAuth calendar account.
        
        Args:
            recruiter_email: Recruiter's email address
            recruiter_name: Recruiter's name
            candidate_name: Candidate's name
            candidate_email: Candidate's email address
            candidate_reference_number: Candidate reference (e.g., CI-123456)
            job_role: Job role/title
            scheduled_date: Test start date/time
            db: Database session (required for OAuth token lookup)
            test_duration_hours: Test duration in hours (default from settings)
            
        Returns:
            Created event details or None if failed
        """
        if not self.enabled:
            logger.info("Google Calendar is disabled. Skipping calendar invite for recruiter.")
            return None
        
        try:
            # Ensure service is initialized (requires db session)
            self._ensure_initialized(db)
            
            # Calculate end time
            if test_duration_hours is None:
                test_duration_hours = settings.TEST_DURATION_HOURS
            end_date = scheduled_date + timedelta(hours=test_duration_hours)
            
            # Format dates
            start_time = self._format_datetime_for_calendar(scheduled_date)
            end_time = self._format_datetime_for_calendar(end_date)
            
            # Create event description with candidate details
            formatted_date = scheduled_date.strftime("%B %d, %Y at %I:%M %p")
            ref_display = f" ({candidate_reference_number})" if candidate_reference_number else ""
            
            description = f"""Interview Scheduled - Candidate Details

Candidate Name: {candidate_name}{ref_display}
Candidate Email: {candidate_email}
Job Role: {job_role}
Scheduled Date: {formatted_date} (IST)
Duration: {test_duration_hours} hours

The candidate has been invited to take their technical assessment at the scheduled time.

---
TechInterview Platform
"""
            
            # Create event
            event = {
                'summary': f'Interview Scheduled: {candidate_name} - {job_role}',
                'description': description,
                'start': start_time,
                'end': end_time,
                'attendees': [
                    {
                        'email': recruiter_email,
                        'responseStatus': 'needsAction',
                        'optional': False
                    }
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': settings.CALENDAR_REMINDER_MINUTES},
                    ],
                },
                'guestsCanInviteOthers': False,
                'guestsCanModify': False,
                'guestsCanSeeOtherGuests': True,
                'colorId': '10',  # Green color to distinguish from candidate events
            }
            
            # Insert event
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all',  # Send email notifications to attendees
                sendNotifications=True,  # Enable notifications
                conferenceDataVersion=0
            ).execute()
            
            logger.info(
                f"Successfully created calendar event for recruiter {recruiter_email}. "
                f"Event ID: {created_event.get('id')}"
            )
            
            return {
                'event_id': created_event.get('id'),
                'event_link': created_event.get('htmlLink'),
                'status': 'created'
            }
            
        except ValueError as e:
            # Calendar not authorized
            logger.warning(f"Calendar not authorized: {e}")
            return None
        except HttpError as e:
            logger.error(f"Google Calendar API error for recruiter {recruiter_email}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create calendar event for recruiter {recruiter_email}: {e}", exc_info=True)
            return None


# Create singleton instance
try:
    calendar_service = CalendarService()
except Exception as e:
    logger.error(f"Failed to create calendar service singleton: {e}")
    # Create a dummy service that does nothing
    class DummyCalendarService:
        enabled = False
        async def create_candidate_calendar_event(self, *args, **kwargs):
            return None
        async def create_recruiter_calendar_event(self, *args, **kwargs):
            return None
    calendar_service = DummyCalendarService()

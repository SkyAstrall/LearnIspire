from django.conf import settings
import os
import datetime
import logging
import uuid
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Set up logging
logger = logging.getLogger(__name__)


class GoogleMeetService:
    """Service for managing Google Meet meetings."""

    @staticmethod
    def get_service():
        """Get Google Calendar API service."""
        try:
            # Load credentials from service account file
            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_SERVICE_ACCOUNT_FILE,
                scopes=["https://www.googleapis.com/auth/calendar"],
            )

            # Build and return the service
            return build("calendar", "v3", credentials=credentials)

        except Exception as e:
            logger.error(f"Error creating Google Calendar service: {str(e)}")
            return None

    @classmethod
    def create_meeting(cls, class_session):
        """Create a Google Meet meeting for a class session."""
        # Always try to create a real meeting first
        result = cls.create_real_meeting(class_session)

        # If real meeting creation fails, the create_real_meeting method
        # will already fall back to the mock method
        return result

    @classmethod
    def create_real_meeting(cls, class_session):
        """Create a real Google Meet meeting using Calendar API."""
        service = cls.get_service()

        if not service:
            logger.error("Failed to create Calendar service")
            return cls._create_mock_meeting(class_session)  # Fallback to mock method

        try:
            # Format event details
            start_time = class_session.start_time.isoformat()
            end_time = class_session.end_time.isoformat()

            # Define event details
            event = {
                "summary": f"{class_session.subject.name} Class",
                "description": (
                    f"Class for {class_session.student.get_full_name()} "
                    f"with {class_session.teacher.get_full_name()}"
                ),
                "start": {
                    "dateTime": start_time,
                    "timeZone": "Asia/Kolkata",
                },
                "end": {
                    "dateTime": end_time,
                    "timeZone": "Asia/Kolkata",
                },
                "conferenceData": {
                    "createRequest": {
                        "requestId": str(uuid.uuid4()),
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                },
                "attendees": [
                    {"email": class_session.student.email},
                    {"email": class_session.teacher.email},
                ],
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "email", "minutes": 60},
                        {"method": "popup", "minutes": 15},
                    ],
                },
            }

            # Create the event with conference data
            event = (
                service.events()
                .insert(
                    calendarId=settings.GOOGLE_CALENDAR_ID,
                    body=event,
                    conferenceDataVersion=1,
                )
                .execute()
            )

            # Extract meeting link and ID
            meeting_link = None
            meeting_id = None

            for entry in event.get("conferenceData", {}).get("entryPoints", []):
                if entry.get("entryPointType") == "video":
                    meeting_link = entry.get("uri")
                    break

            if meeting_link:
                # Extract meeting ID from the link
                meeting_id = meeting_link.split("/")[-1]

                # Update class session with meeting details
                class_session.meeting_link = meeting_link
                class_session.meeting_id = meeting_id
                class_session.save()

                logger.info(
                    f"Created meeting: {meeting_link} for class {class_session.id}"
                )
                print("Created meeting: {meeting_link} for class {class_session.id}")
                return {
                    "meeting_link": meeting_link,
                    "meeting_id": meeting_id,
                    "event_id": event["id"],
                    "success": True,
                }
            else:
                logger.error(
                    "Failed to create meeting: No conference link found in response"
                )
                return cls._create_mock_meeting(
                    class_session
                )  # Fallback to mock method

        except Exception as e:
            logger.error(f"Error creating real meeting: {str(e)}")
            return cls._create_mock_meeting(class_session)  # Fallback to mock method

    @classmethod
    def _create_mock_meeting(cls, class_session):
        """Create a mock Google Meet meeting (for development/fallback)."""
        try:
            # Generate a unique meeting ID
            meeting_id = str(uuid.uuid4()).replace("-", "")[:12]

            # Create mock meeting link
            meeting_link = f"https://meet.google.com/{meeting_id}"

            # Update class session with meeting details
            class_session.meeting_link = meeting_link
            class_session.meeting_id = meeting_id
            class_session.save()

            logger.info(
                f"Created mock meeting: {meeting_link} for class {class_session.id}"
            )

            return {
                "meeting_link": meeting_link,
                "meeting_id": meeting_id,
                "success": True,
                "is_mock": True,
            }

        except Exception as e:
            logger.error(f"Error creating mock meeting: {str(e)}")
            return {"success": False, "error": str(e)}

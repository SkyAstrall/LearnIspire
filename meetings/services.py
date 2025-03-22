from django.conf import settings
import os
import datetime
import logging
import uuid
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Set up logging
logger = logging.getLogger(__name__)


class GoogleMeetService:
    """Service for managing Google Meet meetings."""


    @classmethod
    def create_real_meeting(cls, class_session):
        """Create a real Google Meet meeting using Calendar API."""
        print(f"Attempting to create real meeting for class {class_session.id}")

            # Try to get service using settings
        SERVICE_ACCOUNT_FILE = "edulance-452011-f1970b2af93f.json"
        USER_EMAIL = "admin@learnispire.com"
        credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/calendar"],
        subject=USER_EMAIL,  # Impersonate this user
        )

        service = build("calendar", "v3", credentials=credentials)
                
        


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
                    calendarId='primary',
                    body=event,
                    conferenceDataVersion=1,
                )
                .execute()
            )


            # Extract meeting link and ID
            meeting_link = event.get("hangoutLink")

            if not meeting_link:
                # Try to get meeting link from conferenceData
                for entry in event.get("conferenceData", {}).get("entryPoints", []):
                    if entry.get("entryPointType") == "video":
                        meeting_link = entry.get("uri")
                        break

            if meeting_link:
                # Extract meeting ID from the link
                meeting_id_match = re.search(
                    r"meeting\.google\.com/([a-zA-Z0-9-]+)", meeting_link
                )
                meeting_id = meeting_id_match.group(1) if meeting_id_match else None

                if not meeting_id:
                    # Try alternate format
                    parts = meeting_link.split("/")
                    meeting_id = parts[-1] if parts else None

                # Update class session with meeting details
                if meeting_link and meeting_id:
                    class_session.meeting_link = meeting_link
                    class_session.meeting_id = meeting_id
                    class_session.save()

                    logger.info(
                        f"Meeting created successfully: {meeting_link} for class {class_session.id}"
                    )
                    return {
                        "meeting_link": meeting_link,
                        "meeting_id": meeting_id,
                        "event_id": event["id"],
                        "success": True,
                    }

            print("Failed to extract meeting link/ID from event response")
            return False

        except Exception as e:
            print(f"Error creating real meeting: {str(e)}")
            return False

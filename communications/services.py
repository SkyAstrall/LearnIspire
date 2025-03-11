from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from .models import Notification, NotificationTemplate
import logging

# Set up logging
logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for sending WhatsApp messages via Twilio."""

    @staticmethod
    def get_client():
        """Get Twilio client."""
        return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    @staticmethod
    def format_phone_number(phone_number):
        """Ensure phone number is in international format."""
        # Add + if not present
        if not phone_number.startswith("+"):
            phone_number = "+" + phone_number

        return phone_number

    @classmethod
    def send_message(cls, user, content, template=None):
        """Send WhatsApp message to user."""
        try:
            # Create notification record
            notification = Notification.objects.create(
                user=user,
                template=template,
                content=content,
                channel="WHATSAPP",
                status="PENDING",
            )

            # Format phone number for WhatsApp
            to_phone = cls.format_phone_number(user.phone_number)

            # Get Twilio client
            client = cls.get_client()

            # Send message
            message = client.messages.create(
                from_=f"whatsapp:{settings.TWILIO_WHATSAPP_FROM}",
                body=content,
                to=f"whatsapp:{to_phone}",
            )

            # Update notification record
            notification.mark_as_sent(message.sid)

            logger.info(f"WhatsApp message sent to {to_phone}, SID: {message.sid}")
            return notification

        except TwilioRestException as e:
            logger.error(f"Twilio error: {str(e)}")
            if notification:
                notification.mark_as_failed()
            return None
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            if notification:
                notification.mark_as_failed()
            return None

    @classmethod
    def send_template_message(cls, user, template_type, context=None):
        """Send templated WhatsApp message."""
        try:
            # Get active template
            template = NotificationTemplate.objects.filter(
                template_type=template_type, is_active=True
            ).first()

            if not template:
                logger.error(f"No active template found for type: {template_type}")
                return None

            # Format content with context
            context = context or {}
            content = template.content

            for key, value in context.items():
                content = content.replace(f"{{{key}}}", str(value))

            # Send message
            return cls.send_message(user, content, template)

        except Exception as e:
            logger.error(f"Error sending template message: {str(e)}")
            return None

    @classmethod
    def send_class_reminder(cls, class_session):
        """Send class reminder to student and teacher."""
        context = {
            "subject": class_session.subject.name,
            "date": class_session.start_time.strftime("%d-%m-%Y"),
            "time": class_session.start_time.strftime("%H:%M"),
            "teacher_name": class_session.teacher.get_full_name(),
            "student_name": class_session.student.get_full_name(),
            "meeting_link": class_session.meeting_link,
        }

        # Send to student
        student_notification = cls.send_template_message(
            class_session.student, "CLASS_REMINDER", context
        )

        # Send to teacher
        teacher_notification = cls.send_template_message(
            class_session.teacher, "CLASS_REMINDER", context
        )

        return student_notification, teacher_notification

    @classmethod
    def send_demo_scheduled_notification(cls, class_session):
        """Send demo class scheduled notification."""
        context = {
            "subject": class_session.subject.name,
            "date": class_session.start_time.strftime("%d-%m-%Y"),
            "time": class_session.start_time.strftime("%H:%M"),
            "teacher_name": class_session.teacher.get_full_name(),
            "student_name": class_session.student.get_full_name(),
        }

        # Send to student
        student_notification = cls.send_template_message(
            class_session.student, "DEMO_SCHEDULED", context
        )

        # Send to teacher
        teacher_notification = cls.send_template_message(
            class_session.teacher, "DEMO_SCHEDULED", context
        )

        return student_notification, teacher_notification

    @classmethod
    def send_payment_confirmation(cls, payment):
        """Send payment confirmation to student."""
        context = {
            "amount": payment.amount,
            "transaction_id": payment.transaction_id,
            "date": payment.payment_date.strftime("%d-%m-%Y"),
            "month_year": payment.month_year.strftime("%B %Y"),
        }

        return cls.send_template_message(
            payment.student, "PAYMENT_CONFIRMATION", context
        )

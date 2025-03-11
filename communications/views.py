from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import logging

from accounts.models import CustomUser
from .models import Notification
from .services import WhatsAppService

# Set up logging
logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(View):
    """Webhook for receiving WhatsApp messages from Twilio."""

    def post(self, request):
        try:
            # Parse incoming message data
            message_sid = request.POST.get("MessageSid")
            from_number = request.POST.get("From", "").replace("whatsapp:", "")
            body = request.POST.get("Body", "")

            logger.info(f"Received WhatsApp message: {message_sid} from {from_number}")

            # Try to find user by phone number
            try:
                user = CustomUser.objects.get(phone_number__endswith=from_number[-10:])

                # Process message (e.g., if it's a reply to a specific notification)
                # This can be extended based on your specific use cases

                return HttpResponse(status=200)
            except CustomUser.DoesNotExist:
                logger.warning(f"No user found for phone number: {from_number}")
                return HttpResponse(status=200)

        except Exception as e:
            logger.error(f"Error processing WhatsApp webhook: {str(e)}")
            return HttpResponse(status=500)

    def get(self, request):
        # Twilio will make a GET request to validate the webhook URL
        return HttpResponse("WhatsApp Webhook Endpoint", status=200)


@method_decorator(csrf_exempt, name="dispatch")
class DeliveryStatusWebhookView(View):
    """Webhook for receiving delivery status updates from Twilio."""

    def post(self, request):
        try:
            # Parse delivery status data
            message_sid = request.POST.get("MessageSid")
            message_status = request.POST.get("MessageStatus")

            logger.info(
                f"Received delivery status update: {message_sid} - {message_status}"
            )

            # Update notification status
            if message_sid:
                notification = Notification.objects.filter(
                    provider_id=message_sid
                ).first()
                if notification:
                    if message_status == "delivered":
                        notification.mark_as_delivered()
                    elif message_status in ["failed", "undelivered"]:
                        notification.mark_as_failed()

                    logger.info(
                        f"Updated notification {notification.id} status to {notification.status}"
                    )

            return HttpResponse(status=200)

        except Exception as e:
            logger.error(f"Error processing delivery status webhook: {str(e)}")
            return HttpResponse(status=500)

    def get(self, request):
        # Return simple response for webhook validation
        return HttpResponse("Delivery Status Webhook Endpoint", status=200)


class SendNotificationView(LoginRequiredMixin, View):
    """View for manually sending a notification to a user (admin only)."""

    def get(self, request, user_id):
        if not request.user.is_admin_user:
            messages.error(request, "Access denied. Admin account required.")
            return redirect("admin_dashboard:home")

        user = get_object_or_404(CustomUser, id=user_id)

        # Get notification templates
        from .models import NotificationTemplate

        templates = NotificationTemplate.objects.filter(is_active=True)

        context = {
            "user": user,
            "templates": templates,
        }

        return render(request, "communications/send_notification.html", context)

    def post(self, request, user_id):
        if not request.user.is_admin_user:
            messages.error(request, "Access denied. Admin account required.")
            return redirect("admin_dashboard:home")

        user = get_object_or_404(CustomUser, id=user_id)
        template_id = request.POST.get("template")
        custom_message = request.POST.get("custom_message")

        if template_id:
            # Send templated message
            from .models import NotificationTemplate

            template = get_object_or_404(NotificationTemplate, id=template_id)

            # Get dynamic context variables
            context = {}
            for key in request.POST.keys():
                if key.startswith("var_"):
                    var_name = key[4:]  # Remove 'var_' prefix
                    context[var_name] = request.POST.get(key)

            notification = WhatsAppService.send_template_message(
                user, template.template_type, context
            )

        elif custom_message:
            # Send custom message
            notification = WhatsAppService.send_message(user, custom_message)

        else:
            messages.error(
                request, "Either a template or custom message must be provided."
            )
            return redirect("communications:send_notification", user_id=user_id)

        if notification:
            messages.success(request, f"Notification sent to {user.get_full_name()}.")
        else:
            messages.error(request, "Failed to send notification. Please try again.")

        # Redirect back to user detail page
        if user.is_student:
            return redirect(
                "admin_dashboard:student_detail", student_id=user.student_profile.id
            )
        elif user.is_teacher:
            return redirect(
                "admin_dashboard:teacher_detail", teacher_id=user.teacher_profile.id
            )
        else:
            return redirect("admin_dashboard:home")

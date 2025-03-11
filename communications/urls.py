from django.urls import path
from . import views

app_name = "communications"

urlpatterns = [
    # WhatsApp webhook
    path(
        "webhook/whatsapp/",
        views.WhatsAppWebhookView.as_view(),
        name="whatsapp_webhook",
    ),
    # Notification delivery status
    path(
        "webhook/delivery-status/",
        views.DeliveryStatusWebhookView.as_view(),
        name="delivery_status",
    ),
    # Manual notification sending
    path(
        "send-notification/<int:user_id>/",
        views.SendNotificationView.as_view(),
        name="send_notification",
    ),
]

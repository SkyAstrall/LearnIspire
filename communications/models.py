from django.db import models
from django.utils import timezone


class NotificationTemplate(models.Model):
    """Model for storing WhatsApp notification templates."""

    TEMPLATE_TYPES = (
        ("VERIFICATION", "Account Verification"),
        ("CLASS_REMINDER", "Class Reminder"),
        ("PAYMENT_REMINDER", "Payment Reminder"),
        ("DEMO_SCHEDULED", "Demo Class Scheduled"),
        ("CLASS_SCHEDULED", "Class Scheduled"),
        ("PAYMENT_CONFIRMATION", "Payment Confirmation"),
        ("TEACHER_APPROVAL", "Teacher Approval"),
    )

    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    template_id = models.CharField(
        max_length=100, help_text="Twilio WhatsApp template ID"
    )
    content = models.TextField(
        help_text="Template content with variables in {variable} format"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_template_type_display()} - {self.name}"

    class Meta:
        unique_together = ["template_type", "name"]


class Notification(models.Model):
    """Model for tracking sent notifications."""

    NOTIFICATION_STATUS = (
        ("PENDING", "Pending"),
        ("SENT", "Sent"),
        ("DELIVERED", "Delivered"),
        ("FAILED", "Failed"),
    )

    NOTIFICATION_CHANNELS = (
        ("WHATSAPP", "WhatsApp"),
        ("SMS", "SMS"),
        ("EMAIL", "Email"),
    )

    user = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE, related_name="notifications"
    )
    template = models.ForeignKey(
        NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True
    )
    subject = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    channel = models.CharField(
        max_length=10, choices=NOTIFICATION_CHANNELS, default="WHATSAPP"
    )
    status = models.CharField(
        max_length=10, choices=NOTIFICATION_STATUS, default="PENDING"
    )
    sent_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    provider_id = models.CharField(
        max_length=100, blank=True, help_text="Message ID from provider"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.channel} - {self.get_status_display()}"

    class Meta:
        ordering = ["-created_at"]

    def mark_as_sent(self, provider_id):
        """Mark notification as sent."""
        self.status = "SENT"
        self.provider_id = provider_id
        self.sent_at = timezone.now()
        self.save()

    def mark_as_delivered(self):
        """Mark notification as delivered."""
        self.status = "DELIVERED"
        self.delivered_at = timezone.now()
        self.save()

    def mark_as_failed(self):
        """Mark notification as failed."""
        self.status = "FAILED"
        self.save()

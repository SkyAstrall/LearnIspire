from django.contrib import admin
from .models import NotificationTemplate, Notification


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "template_type",
        "template_id",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = ("template_type", "is_active", "created_at")
    search_fields = ("name", "template_id", "content")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "template_type",
                    "template_id",
                    "content",
                    "is_active",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "template",
        "channel",
        "status",
        "sent_at",
        "delivered_at",
        "provider_id",
        "created_at",
    )
    list_filter = ("channel", "status", "created_at")
    search_fields = ("user__email", "subject", "content", "provider_id")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "sent_at", "delivered_at")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "template",
                    "subject",
                    "content",
                    "channel",
                    "status",
                    "provider_id",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("sent_at", "delivered_at", "created_at", "updated_at"),
            },
        ),
    )

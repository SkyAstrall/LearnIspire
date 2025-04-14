from django.contrib import admin
from .models import Payment, TeacherEarning


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "amount",
        "status",
        "payment_method",
        "payment_date",
        "order_id",
        "transaction_id",
        "month_year",
        "created_at",
    )
    list_filter = ("status", "payment_method", "month_year", "created_at")
    search_fields = (
        "student__email",
        "transaction_id",
        "order_id",
        "payment_details",
    )
    readonly_fields = ("created_at", "updated_at", "payment_date")
    ordering = ("-created_at",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "student",
                    "amount",
                    "status",
                    "payment_method",
                    "month_year",
                    "transaction_id",
                    "order_id",
                    "payment_details",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("payment_date", "created_at", "updated_at"),
            },
        ),
    )


@admin.register(TeacherEarning)
class TeacherEarningAdmin(admin.ModelAdmin):
    list_display = (
        "teacher",
        "month_year",
        "amount",
        "classes_conducted",
        "payment_status",
        "payment_date",
        "payment_reference",
        "created_at",
    )
    list_filter = ("payment_status", "month_year", "created_at")
    search_fields = (
        "teacher__email",
        "payment_reference",
        "notes",
    )
    readonly_fields = ("created_at", "updated_at", "payment_date")
    ordering = ("-month_year",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "teacher",
                    "month_year",
                    "amount",
                    "classes_conducted",
                    "payment_status",
                    "payment_reference",
                    "notes",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("payment_date", "created_at", "updated_at"),
            },
        ),
    )

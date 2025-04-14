from django.contrib import admin
from .models import Availability, Class, ClassMaterial, LeaveRequest


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ("user", "day_of_week", "start_time", "end_time", "is_recurring")
    list_filter = ("day_of_week", "is_recurring")
    search_fields = ("user__email",)
    ordering = ("day_of_week", "start_time")


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "student",
        "teacher",
        "start_time",
        "end_time",
        "status",
        "is_demo",
    )
    list_filter = ("status", "is_demo", "start_time")
    search_fields = ("student__email", "teacher__email", "subject__name")
    ordering = ("-start_time",)


@admin.register(ClassMaterial)
class ClassMaterialAdmin(admin.ModelAdmin):
    list_display = ("title", "class_session", "uploaded_by", "uploaded_at")
    search_fields = ("title", "uploaded_by__email", "class_session__subject__name")
    list_filter = ("uploaded_at",)


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "start_date",
        "end_date",
        "status",
        "reviewed_by",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("user__email", "reviewed_by__email", "reason")
    ordering = ("-created_at",)

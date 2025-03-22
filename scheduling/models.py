from django.db import models
from django.utils import timezone
from accounts.models import CustomUser
from django.core.exceptions import ValidationError

class Availability(models.Model):
    DAYS_OF_WEEK = (
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    )

    user = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE, related_name="availabilities"
    )
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_recurring = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.get_day_of_week_display()} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"

    class Meta:
        ordering = ["day_of_week", "start_time"]
        verbose_name_plural = "Availabilities"

    def clean(self):
        """Validate that start time is before end time."""
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time.")

    @classmethod
    def has_minimum_slots(cls, user, min_slots=3):
        """Check if user has minimum required availability slots."""
        return cls.objects.filter(user=user).count() >= min_slots


class Class(models.Model):
    CLASS_STATUS = (
        ("SCHEDULED", "Scheduled"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
        ("MISSED", "Missed"),
    )

    student = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE, related_name="student_classes"
    )
    teacher = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE, related_name="teacher_classes"
    )
    subject = models.ForeignKey(
        "common.Subject", on_delete=models.CASCADE, related_name="classes"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=CLASS_STATUS, default="SCHEDULED")
    is_demo = models.BooleanField(default=False)
    meeting_link = models.URLField(blank=True)
    meeting_id = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject.name} - {self.student.email} with {self.teacher.email} on {self.start_time.strftime('%d-%m-%Y %H:%M')}"

    class Meta:
        verbose_name_plural = "Classes"
        ordering = ["start_time"]

    def is_upcoming(self):
        """Check if class is upcoming."""
        now = timezone.now()
        return now < self.start_time

    def is_ongoing(self):
        """Check if class is currently ongoing."""
        now = timezone.now()
        return self.start_time <= now <= self.end_time

    def can_join(self):
        """Check if class can be joined (15 minutes before start until end)."""
        now = timezone.now()
        join_window_start = self.start_time - timezone.timedelta(minutes=15)
        return True

    def mark_completed(self):
        """Mark class as completed."""
        self.status = "COMPLETED"
        self.save()


class ClassMaterial(models.Model):
    """Model for class materials uploaded by teachers."""

    class_session = models.ForeignKey(
        Class, on_delete=models.CASCADE, related_name="materials"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="class_materials/")
    uploaded_by = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.class_session}"


class LeaveRequest(models.Model):
    LEAVE_STATUS = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )

    user = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE, related_name="leave_requests"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=LEAVE_STATUS, default="PENDING")
    reviewed_by = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_leave_requests",
    )
    review_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.start_date} to {self.end_date} ({self.get_status_display()})"

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        """Validate date range."""
        if self.start_date > self.end_date:
            raise ValidationError("End date must be on or after start date.")

    def approve(self, admin_user, comments=None):
        """Approve leave request."""
        self.status = "APPROVED"
        self.reviewed_by = admin_user
        if comments:
            self.review_comments = comments
        self.save()

    def reject(self, admin_user, comments=None):
        """Reject leave request."""
        self.status = "REJECTED"
        self.reviewed_by = admin_user
        if comments:
            self.review_comments = comments
        self.save()

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    USER_ROLES = (
        ("student", "Student"),
        ("teacher", "Teacher"),
        ("admin", "Admin"),
    )

    email = models.EmailField(_("email address"), unique=True)
    phone_number = models.CharField(max_length=15, unique=False)
    is_phone_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=10, choices=USER_ROLES, default="student")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "phone_number"]

    def __str__(self):
        return self.email

    @property
    def is_student(self):
        return self.role == "student"

    @property
    def is_teacher(self):
        return self.role == "teacher"

    @property
    def is_admin_user(self):
        return self.role == "admin"


class StudentProfile(models.Model):
    STUDENT_STATUS = (
        ("NEW", "New Registration"),
        ("PRICING_REQUESTED", "Pricing Requested"),
        ("AVAILABILITY_SET", "Availability Set"),
        ("DEMO_PENDING", "Demo Pending"),
        ("DEMO_SCHEDULED", "Demo Scheduled"),
        ("DEMO_ACCEPTED", "Demo Accepted"),
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
    )

    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="student_profile"
    )
    grade = models.ForeignKey(
        "common.Grade", on_delete=models.SET_NULL, null=True, related_name="students"
    )
    board = models.ForeignKey(
        "common.Board", on_delete=models.SET_NULL, null=True, related_name="students"
    )
    status = models.CharField(max_length=20, choices=STUDENT_STATUS, default="NEW")
    selected_subjects = models.ManyToManyField(
        "common.Subject", related_name="interested_students", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    demo_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.email} - {self.get_status_display()}"

    def update_status(self, new_status):
        if new_status in dict(self.STUDENT_STATUS):
            self.status = new_status
            self.save()
            return True
        return False


class TeacherProfile(models.Model):
    TEACHER_STATUS = (
        ("PENDING", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("REJECTED", "Rejected"),
    )

    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="teacher_profile"
    )
    education = models.TextField()
    experience = models.TextField()
    subjects = models.ManyToManyField("common.Subject", related_name="teachers")
    status = models.CharField(max_length=20, choices=TEACHER_STATUS, default="PENDING")
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(
        upload_to="teacher_profiles/", null=True, blank=True
    )
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=30, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    account_holder_name = models.CharField(max_length=100, blank=True)
    branch_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    highest_qualification = models.CharField(max_length=100, blank=True)
    years_of_experience = models.IntegerField(default=0)
    university = models.CharField(max_length=200, blank=True)
    graduation_year = models.IntegerField(default=0)
    specialization = models.CharField(max_length=200, blank=True)
    skills = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.email} - {self.get_status_display()}"

    def update_status(self, new_status):
        if new_status in dict(self.TEACHER_STATUS):
            self.status = new_status
            self.save()
            return True
        return False

    @property
    def is_bank_details_complete(self):
        return bool(self.bank_name and self.account_number and self.ifsc_code)


class PhoneVerification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.phone_number} - {'Verified' if self.is_verified else 'Not Verified'}"

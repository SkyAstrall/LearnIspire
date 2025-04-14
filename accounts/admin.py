from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StudentProfile, TeacherProfile, PhoneVerification


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("email", "username", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "username", "phone_number")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone_number")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Roles", {"fields": ("role",)}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "phone_number",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "grade", "board", "status", "created_at", "updated_at")
    list_filter = ("status", "grade", "board")
    search_fields = ("user__email", "user__username")
    raw_id_fields = ("user",)
    filter_horizontal = ("selected_subjects",)
    ordering = ("-created_at",)


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "status",
        "years_of_experience",
        "highest_qualification",
        "created_at",
    )
    list_filter = ("status", "subjects")
    search_fields = ("user__email", "user__username", "university", "specialization")
    raw_id_fields = ("user",)
    filter_horizontal = ("subjects",)
    ordering = ("-created_at",)


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "phone_number",
        "otp",
        "is_verified",
        "created_at",
        "expires_at",
    )
    list_filter = ("is_verified",)
    search_fields = ("user__email", "phone_number")
    ordering = ("-created_at",)

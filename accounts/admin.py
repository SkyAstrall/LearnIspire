from django.contrib import admin
from .models import CustomUser
# Register your models here.
@admin.register(CustomUser)
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "phone_number", "role"]
    search_fields = ["email", "phone_number"]
    list_filter = ["role"]
    fieldsets = (
        (None, {"fields": ("email", "phone_number", "role")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "phone_number", "role"),
            },
        ),
    )
    ordering = ["email"]
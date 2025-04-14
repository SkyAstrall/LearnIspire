from django.contrib import admin
from .models import Subject, Grade, Board, PricingRule, Configuration


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("order",)


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "grade",
        "board",
        "price_per_session",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_active", "grade", "board", "subject")
    search_fields = ("subject__name", "grade__name", "board__name")
    ordering = ("grade__order", "subject__name")
    autocomplete_fields = ("grade", "board", "subject")


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "description")
    search_fields = ("key", "description")

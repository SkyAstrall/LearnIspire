from django.contrib import admin
from .models import PricingRule

@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = ('subject', 'grade', 'board', 'price_per_session', 'is_active')
    list_filter = ('grade', 'board', 'is_active')
    search_fields = ('subject__name', 'grade__name', 'board__name')
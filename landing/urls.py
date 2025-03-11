from django.urls import path
from . import views

app_name = "landing"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("pricing/", views.PricingView.as_view(), name="pricing"),
    path("contact/", views.ContactView.as_view(), name="contact"),
    path("subjects/", views.SubjectsView.as_view(), name="subjects"),
    path("privacy/", views.PrivacyPolicyView.as_view(), name="privacy"),
    path("terms/", views.TermsConditionsView.as_view(), name="terms"),
]

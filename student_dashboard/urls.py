from django.urls import path
from . import views

app_name = "student_dashboard"

urlpatterns = [
    path("", views.StudentDashboardHomeView.as_view(), name="home"),
    path("profile/", views.StudentProfileView.as_view(), name="profile"),
    path("subjects/", views.SubjectSelectionView.as_view(), name="subject_selection"),
    path("availability/", views.AvailabilitySetupView.as_view(), name="availability"),
    path("demo-request/", views.DemoRequestView.as_view(), name="demo_request"),
    path("classes/", views.ClassesListView.as_view(), name="classes"),
    path(
        "classes/<int:class_id>/", views.ClassDetailView.as_view(), name="class_detail"
    ),
    path(
        "classes/<int:class_id>/join/", views.JoinClassView.as_view(), name="join_class"
    ),
    path(
        "classes/<int:class_id>/feedback/",
        views.DemoFeedbackView.as_view(),
        name="demo_feedback",
    ),
    path("payments/", views.PaymentsView.as_view(), name="payments"),
    path(
        "payments/<int:payment_id>/initiate/",
        views.InitiatePaymentView.as_view(),
        name="initiate_payment",
    ),
]

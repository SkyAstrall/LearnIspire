from django.urls import path
from . import views

app_name = "teacher_dashboard"

urlpatterns = [
    path("", views.TeacherDashboardHomeView.as_view(), name="home"),
    path("profile/", views.TeacherProfileView.as_view(), name="profile"),
    path("availability/", views.AvailabilitySetupView.as_view(), name="availability"),
    path("classes/", views.ClassesListView.as_view(), name="classes"),
    path(
        "classes/<int:class_id>/", views.ClassDetailView.as_view(), name="class_detail"
    ),
    path(
        "classes/<int:class_id>/join/", views.JoinClassView.as_view(), name="join_class"
    ),
    path(
        "classes/<int:class_id>/complete/",
        views.CompleteClassView.as_view(),
        name="complete_class",
    ),
    path(
        "classes/<int:class_id>/upload-material/",
        views.UploadMaterialView.as_view(),
        name="upload_material",
    ),
    path("leave-requests/", views.LeaveRequestView.as_view(), name="leave_request"),
    path("earnings/", views.EarningsView.as_view(), name="earnings"),
    path("bank-details/", views.BankDetailsView.as_view(), name="bank_details"),
]

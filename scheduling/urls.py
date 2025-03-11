from django.urls import path
from . import views

app_name = "scheduling"

urlpatterns = [
    # Class management
    path(
        "availability/", views.AvailabilityListView.as_view(), name="availability_list"
    ),
    path("classes/", views.ClassListView.as_view(), name="class_list"),
    path(
        "classes/<int:class_id>/", views.ClassDetailView.as_view(), name="class_detail"
    ),
    # Leave requests
    path("leaves/", views.LeaveRequestListView.as_view(), name="leave_list"),
    path("leaves/create/", views.LeaveRequestCreateView.as_view(), name="leave_create"),
    # API endpoints
    path(
        "api/check-availability/", views.check_availability, name="check_availability"
    ),
]

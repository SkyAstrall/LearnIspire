from django.urls import path
from . import views

app_name = "meetings"

urlpatterns = [
    path("join/<int:class_id>/", views.JoinMeetingView.as_view(), name="join"),
    path("end/<int:class_id>/", views.EndMeetingView.as_view(), name="end"),
    path(
        "feedback/<int:class_id>/", views.MeetingFeedbackView.as_view(), name="feedback"
    ),
]

from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # Phone verification
    path("verify-phone/", views.VerifyPhoneView.as_view(), name="verify_phone"),
    path("resend-otp/", views.ResendOTPView.as_view(), name="resend_otp"),
    # Profile management
    path(
        "student-profile/",
        views.StudentProfileUpdateView.as_view(),
        name="student_profile",
    ),
    path(
        "teacher-profile/",
        views.TeacherProfileUpdateView.as_view(),
        name="teacher_profile",
    ),
    # Login redirect
    path("login-redirect/", views.LoginRedirectView.as_view(), name="login_redirect"),
]

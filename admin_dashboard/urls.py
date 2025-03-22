from django.urls import path
from . import views

app_name = "admin_dashboard"

urlpatterns = [
    path("", views.AdminDashboardHomeView.as_view(), name="home"),
    # Student management
    path("students/", views.StudentListView.as_view(), name="students"),
    path(
        "students/<int:student_id>/",
        views.StudentDetailView.as_view(),
        name="student_detail",
    ),
    # Teacher management
    path("teachers/", views.TeacherListView.as_view(), name="teachers"),
    path(
        "teachers/<int:teacher_id>/",
        views.TeacherDetailView.as_view(),
        name="teacher_detail",
    ),
    path(
        "teachers/<int:teacher_id>/approval/",
        views.TeacherApprovalView.as_view(),
        name="teacher_approval",
    ),
    # Demo management
    path("pending-demos/", views.DemoPendingListView.as_view(), name="pending_demos"),
    path(
        "schedule-demo/<int:student_id>/",
        views.ScheduleDemoView.as_view(),
        name="schedule_demo",
    ),
    # Class scheduling
    path(
        "schedule-classes/<int:student_id>/",
        views.ClassSchedulingView.as_view(),
        name="schedule_classes",
    ),
    # Leave management
    path("leave-requests/", views.LeaveRequestsView.as_view(), name="leave_requests"),
    path(
        "leave-requests/<int:leave_id>/action/",
        views.LeaveRequestActionView.as_view(),
        name="leave_request_action",
    ),
    # Financial management
    path("payments/", views.PaymentsView.as_view(), name="payments"),
    path(
        "teacher-earnings/",
        views.TeacherEarningsView.as_view(),
        name="teacher_earnings",
    ),
    path(
        "teacher-earnings/<int:earning_id>/process/",
        views.ProcessTeacherPaymentView.as_view(),
        name="process_teacher_payment",
    ),
    path(
        "activate-approved-teachers/",
        views.ActivateApprovedTeachersView.as_view(),
        name="activate_approved_teachers",
    ),
    path(
        "api/teacher-availability/<int:teacher_id>/",
        views.TeacherAvailabilityAPI.as_view(),
        name="teacher_availability_api",
    ),
]

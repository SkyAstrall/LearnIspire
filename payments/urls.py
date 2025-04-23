from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    # Payment processing
    path(
        "initiate/",
        views.InitiatePaymentView.as_view(),
        name="initiate",
    ),
    path(
        "<str:status_type>/",
        views.PaymentCallbackView.as_view(),
        name="payment_callback",
    ),
    path("success/", views.PaymentSuccessView.as_view(), name="success"),
    path("failure/", views.PaymentFailureView.as_view(), name="failure"),
    # Payment API endpoints
    path("verify/<str:order_id>/", views.VerifyPaymentView.as_view(), name="verify"),
    # Teacher earnings
    path("earnings/", views.TeacherEarningsView.as_view(), name="earnings"),
    path(
        "earnings/<int:year>/<int:month>/",
        views.MonthlyEarningsView.as_view(),
        name="monthly_earnings",
    ),
]

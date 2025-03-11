from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Payment, TeacherEarning
from .services import PayUService
from accounts.models import StudentProfile


class InitiatePaymentView(LoginRequiredMixin, View):
    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id, student=request.user)

        # Check if payment is pending
        if payment.status not in ["PENDING", "INITIATED"]:
            messages.error(request, "This payment has already been processed.")
            return redirect("student_dashboard:payments")

        # Generate payment request
        payment_request = PayUService.create_payment_request(
            request.user, payment.amount, payment.month_year
        )

        if not payment_request["success"]:
            messages.error(request, "Failed to initiate payment. Please try again.")
            return redirect("student_dashboard:payments")

        # Render payment form
        return render(
            request,
            "payments/initiate.html",
            {
                "payment": payment,
                "params": payment_request["params"],
                "payu_url": payment_request["url"],
            },
        )


@method_decorator(csrf_exempt, name="dispatch")
class PaymentSuccessView(View):
    def post(self, request):
        # Process payment response from PayU
        response = PayUService.handle_payment_response(request.POST)

        if response["success"]:
            payment = response["payment"]

            if response["status"] == "success":
                messages.success(request, "Payment completed successfully!")

                # Send confirmation message via WhatsApp
                from communications.services import WhatsAppService

                WhatsAppService.send_payment_confirmation(payment)

            else:
                messages.warning(
                    request, "Payment was not successful. Please try again."
                )

            return redirect("student_dashboard:payments")
        else:
            messages.error(
                request,
                f"Error processing payment: {response.get('error', 'Unknown error')}",
            )
            return redirect("student_dashboard:payments")

    def get(self, request):
        # Redirect to payments page
        messages.info(request, "Redirected from payment gateway.")
        return redirect("student_dashboard:payments")


@method_decorator(csrf_exempt, name="dispatch")
class PaymentFailureView(View):
    def post(self, request):
        # Process failed payment response from PayU
        messages.error(request, "Payment was not successful. Please try again.")
        return redirect("student_dashboard:payments")

    def get(self, request):
        # Redirect to payments page
        messages.error(request, "Payment was cancelled or failed. Please try again.")
        return redirect("student_dashboard:payments")


class VerifyPaymentView(View):
    def get(self, request, order_id):
        # Verify payment status
        try:
            payment = Payment.objects.get(order_id=order_id)

            return JsonResponse(
                {
                    "success": True,
                    "status": payment.status,
                    "amount": str(payment.amount),
                    "transaction_id": payment.transaction_id or "",
                    "payment_date": (
                        payment.payment_date.isoformat()
                        if payment.payment_date
                        else None
                    ),
                }
            )
        except Payment.DoesNotExist:
            return JsonResponse({"success": False, "error": "Payment not found"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})


class TeacherEarningsView(LoginRequiredMixin, View):
    template_name = "payments/earnings.html"

    def get(self, request):
        if not request.user.is_teacher:
            messages.error(request, "Access denied. Teacher account required.")
            return redirect("landing:home")

        # Get earnings for the past 6 months
        now = timezone.now()
        earnings = []

        for i in range(6):
            month = now.month - i
            year = now.year

            if month <= 0:
                month += 12
                year -= 1

            month_date = timezone.datetime(year, month, 1).date()

            # Get or calculate earnings
            month_earnings = TeacherEarning.objects.filter(
                teacher=request.user, month_year__year=year, month_year__month=month
            ).first()

            if not month_earnings:
                month_earnings = TeacherEarning.calculate_for_teacher_month(
                    request.user, month_date
                )

            earnings.append(month_earnings)

        context = {
            "earnings": earnings,
        }

        return render(request, self.template_name, context)


class MonthlyEarningsView(LoginRequiredMixin, View):
    template_name = "payments/monthly_earnings.html"

    def get(self, request, year, month):
        if not request.user.is_teacher:
            messages.error(request, "Access denied. Teacher account required.")
            return redirect("landing:home")

        # Get month details
        month_date = timezone.datetime(year, month, 1).date()

        # Get earnings for the month
        earnings = TeacherEarning.objects.filter(
            teacher=request.user, month_year__year=year, month_year__month=month
        ).first()

        if not earnings:
            earnings = TeacherEarning.calculate_for_teacher_month(
                request.user, month_date
            )

        # Get classes for the month
        from scheduling.models import Class

        classes = Class.objects.filter(
            teacher=request.user, start_time__year=year, start_time__month=month
        ).order_by("start_time")

        context = {
            "earnings": earnings,
            "classes": classes,
            "month_date": month_date,
        }

        return render(request, self.template_name, context)

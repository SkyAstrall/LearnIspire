from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.urls import reverse

from .models import Payment, TeacherEarning
from .services import PayUService
from accounts.models import StudentProfile, CustomUser
import logging

# Set up logger
logger = logging.getLogger('payments')

class InitiatePaymentView(LoginRequiredMixin, View):
    """View to initiate a payment for monthly classes."""
    
    def calculate_monthly_amount(self, user):
        """Calculate monthly amount based on selected subjects."""
        try:
            profile = user.student_profile
            selected_subjects = profile.selected_subjects.all()
            
            total_amount = 0
            for subject in selected_subjects:
                # Get pricing rule for this subject and student's grade/board
                from pricing.models import PricingRule
                
                pricing_rule = PricingRule.objects.filter(
                    subject=subject,
                    grade=profile.grade,
                    board=profile.board,
                    is_active=True
                ).first()
                
                if pricing_rule:
                    # Calculate monthly cost (price per session × 3 classes/week × 4 weeks)
                    subject_monthly = pricing_rule.price_per_session * 12
                    total_amount += subject_monthly
            
            # If no subjects or pricing rules found, use default amount
            if total_amount == 0:
                total_amount = 2000.00
                
            return total_amount
            
        except Exception as e:
            logger.exception(f"Error calculating payment amount: {str(e)}")
            return 2000.00  # Default fallback amount
    
    def get(self, request):
        """Show payment form with all details ready to submit to PayU."""
        try:
            logger.info(f"Preparing payment page for user: {request.user.email}")
            # Get current month
            current_date = timezone.now().date()
            
            # Check if payment for current month already exists
            existing_payment = Payment.objects.filter(
                student=request.user,
                month_year__year=current_date.year,
                month_year__month=current_date.month,
                status__in=["COMPLETED", "INITIATED"]
            ).first()
            
            if existing_payment:
                if existing_payment.status == "COMPLETED":
                    messages.info(request, "You've already paid for this month.")
                    return redirect("student_dashboard:payments")
                else:
                    # Continue with existing payment
                    payment = existing_payment
            else:
                # Calculate amount based on selected subjects
                amount = self.calculate_monthly_amount(request.user)
                
                # Create payment record with INITIATED status
                payment = Payment(
                    student=request.user,
                    amount=amount,
                    month_year=current_date.replace(day=1),
                    status="INITIATED"  # Changed from PENDING to INITIATED
                )
                payment.save()
                logger.info(f"Created new payment: {payment.order_id}")
            
            # Get student profile and selected subjects
            try:
                profile = request.user.student_profile
                selected_subjects = profile.selected_subjects.all()
            except:
                profile = None
                selected_subjects = []
            
            # Generate payment parameters
            params = payment.generate_payment_params()
            payu_url = PayUService.get_payu_url()
            
            logger.info(f"Payment page ready with order ID: {payment.order_id}")
            
            return render(request, "payments/payment.html", {
                "payment": payment,
                "params": params,
                "payu_url": payu_url,
                "profile": profile,
                "selected_subjects": selected_subjects,
                "debug": settings.DEBUG  # Only show debug info in DEBUG mode
            })
        
        except Exception as e:
            logger.exception(f"Exception in payment page preparation: {str(e)}")
            messages.error(request, f"Error preparing payment page: {str(e)}")
            return redirect("student_dashboard:payments")
    
    def post(self, request):
        """
        This method is now just a fallback in case someone submits the form
        to this URL instead of directly to the payment gateway.
        """
        try:
            logger.info(f"POST request to initiate payment for user: {request.user.email}")
            # In case the form on student dashboard submits here, redirect to GET
            # to ensure proper payment initialization
            return self.get(request)
                
        except Exception as e:
            logger.exception(f"Exception in payment initiation: {str(e)}")
            messages.error(request, f"Error initiating payment: {str(e)}")
            return redirect("student_dashboard:payments")


@method_decorator(csrf_exempt, name="dispatch")
class PaymentCallbackView(View):
    """Base view to handle PayU payment callbacks."""
    
    def post(self, request, status_type):
        """Process callback from PayU."""
        logger.info(f"Payment callback received: {status_type}")
        logger.debug(f"Callback POST data: {request.POST}")
        
        # Convert QueryDict to regular dict
        params = {k: v for k, v in request.POST.items()}
        
        # Process the payment response
        response = PayUService.handle_payment_response(params)
        
        if response["success"]:
            payment = response["payment"]
            
            if response["status"] == "success":
                logger.info(f"Payment successful: {payment.order_id}")
                messages.success(request, "Payment completed successfully!")
                
                # Send confirmation message if required
                try:
                    from communications.services import WhatsAppService
                    WhatsAppService.send_payment_confirmation(payment)
                except Exception as e:
                    logger.error(f"Error sending payment confirmation: {str(e)}")
                    # Log error but don't fail the transaction
                    pass
                    
            else:
                logger.warning(f"Payment failed: {payment.order_id}")
                messages.warning(request, "Payment was not successful. Please try again.")
            
            return redirect("student_dashboard:payments")
        else:
            logger.error(f"Error processing payment callback: {response.get('error', 'Unknown error')}")
            messages.error(request, f"Error processing payment: {response.get('error', 'Unknown error')}")
            return redirect("student_dashboard:payments")


@method_decorator(csrf_exempt, name="dispatch")
class PaymentSuccessView(View):
    """View to handle successful payments."""
    
    def post(self, request):
        """Process successful payment callback."""
        logger.info("Payment success callback received")
        logger.debug(f"Success callback POST data: {request.POST}")
        
        # Convert QueryDict to regular dict
        params = {k: v for k, v in request.POST.items()}
        
        # Process the payment response
        response = PayUService.handle_payment_response(params)
        
        if response["success"]:
            payment = response["payment"]
            
            if response["status"] == "success":
                logger.info(f"Payment successful: {payment.order_id}")
                messages.success(request, "Payment completed successfully!")
                
                # Send confirmation message if required
                try:
                    from communications.services import WhatsAppService
                    WhatsAppService.send_payment_confirmation(payment)
                except Exception as e:
                    logger.error(f"Error sending payment confirmation: {str(e)}")
                    # Log error but don't fail the transaction
                    pass
                    
            else:
                logger.warning(f"Payment failed despite success callback: {payment.order_id}")
                messages.warning(request, "Payment was not successful. Please try again.")
            
            return redirect("student_dashboard:payments")
        else:
            logger.error(f"Error processing success callback: {response.get('error', 'Unknown error')}")
            messages.error(request, f"Error processing payment: {response.get('error', 'Unknown error')}")
            return redirect("student_dashboard:payments")
    
    def get(self, request):
        """Handle GET request (redirect from payment gateway)."""
        logger.info("Payment success GET request received")
        messages.info(request, "Redirected from payment gateway.")
        return redirect("student_dashboard:payments")


@method_decorator(csrf_exempt, name="dispatch")
class PaymentFailureView(View):
    """View to handle failed payments."""
    
    def post(self, request):
        """Process failed payment callback."""
        logger.info("Payment failure callback received")
        logger.debug(f"Failure callback POST data: {request.POST}")
        
        # Convert QueryDict to regular dict
        params = {k: v for k, v in request.POST.items()}
        
        # Process the payment response
        response = PayUService.handle_payment_response(params)
        
        if response["success"]:
            payment = response["payment"]
            logger.info(f"Payment failure processed: {payment.order_id}")
            # Update UI based on payment status
            messages.error(request, "Payment was not successful. Please try again.")
        else:
            logger.error(f"Error processing failure callback: {response.get('error', 'Unknown error')}")
            messages.error(request, f"Error processing payment: {response.get('error', 'Unknown error')}")
        
        return redirect("student_dashboard:payments")
    
    def get(self, request):
        """Handle GET request (redirect from payment gateway)."""
        logger.info("Payment failure GET request received")
        messages.error(request, "Payment was cancelled or failed. Please try again.")
        return redirect("student_dashboard:payments")


class VerifyPaymentView(View):
    """View to verify payment status."""
    
    def get(self, request, order_id):
        """Verify payment status by order ID."""
        try:
            logger.info(f"Verifying payment: {order_id}")
            payment = Payment.objects.get(order_id=order_id)
            
            response_data = {
                "success": True,
                "status": payment.status,
                "amount": str(payment.amount),
                "transaction_id": payment.transaction_id or "",
                "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
            }
            
            logger.info(f"Payment verification result: {response_data}")
            return JsonResponse(response_data)
        except Payment.DoesNotExist:
            logger.error(f"Payment not found: {order_id}")
            return JsonResponse({"success": False, "error": "Payment not found"})
        except Exception as e:
            logger.exception(f"Error verifying payment: {str(e)}")
            return JsonResponse({"success": False, "error": str(e)})


class TeacherEarningsView(LoginRequiredMixin, View):
    template_name = "payments/earnings.html"
    
    def get(self, request):
        if not request.user.is_teacher:
            logger.warning(f"Non-teacher user attempted to access earnings: {request.user.email}")
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
                teacher=request.user, 
                month_year__year=year, 
                month_year__month=month
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
            logger.warning(f"Non-teacher user attempted to access monthly earnings: {request.user.email}")
            messages.error(request, "Access denied. Teacher account required.")
            return redirect("landing:home")
        
        # Get month details
        month_date = timezone.datetime(year, month, 1).date()
        
        # Get earnings for the month
        earnings = TeacherEarning.objects.filter(
            teacher=request.user, 
            month_year__year=year, 
            month_year__month=month
        ).first()
        
        if not earnings:
            earnings = TeacherEarning.calculate_for_teacher_month(
                request.user, month_date
            )
        
        # Get classes for the month
        from scheduling.models import Class
        
        classes = Class.objects.filter(
            teacher=request.user, 
            start_time__year=year, 
            start_time__month=month
        ).order_by("start_time")
        
        context = {
            "earnings": earnings,
            "classes": classes,
            "month_date": month_date,
        }
        
        return render(request, self.template_name, context)
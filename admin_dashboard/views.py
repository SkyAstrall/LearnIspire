from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
import calendar

from accounts.models import CustomUser, StudentProfile, TeacherProfile
from common.models import Subject, Grade, Board, PricingRule
from scheduling.models import Availability, Class, LeaveRequest
from payments.models import Payment, TeacherEarning
from meetings.services import GoogleMeetService
from communications.services import WhatsAppService


class AdminAccessMixin(LoginRequiredMixin):
    """Mixin to ensure only admins can access a view."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "Access denied. Admin account required.")
            return redirect("landing:home")
        return super().dispatch(request, *args, **kwargs)

from django.http import JsonResponse


class TeacherAvailabilityAPI(AdminAccessMixin, View):
    """API endpoint to get teacher availability"""

    def get(self, request, teacher_id):
        try:
            teacher = get_object_or_404(CustomUser, id=teacher_id, role="teacher")

            # Get teacher availability
            availabilities = Availability.objects.filter(user=teacher).order_by(
                "day_of_week", "start_time"
            )

            # Format for JSON response
            availability_data = []
            for slot in availabilities:
                availability_data.append(
                    {
                        "day_of_week": slot.day_of_week,
                        "start_time": slot.start_time.strftime("%I:%M %p"),
                        "end_time": slot.end_time.strftime("%I:%M %p"),
                    }
                )

            # Return JSON response
            return JsonResponse({"success": True, "availability": availability_data})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)


class ActivateApprovedTeachersView(AdminAccessMixin, View):
    """
    Temporary utility view to activate teachers that were previously approved but not set to active.
    """

    def get(self, request):
        # Count how many teachers are in APPROVED status
        approved_count = TeacherProfile.objects.filter(status="APPROVED").count()

        context = {
            "approved_count": approved_count,
            # Add these for sidebar notifications
            "pending_demo_count": StudentProfile.objects.filter(
                status="DEMO_PENDING"
            ).count(),
            "pending_teacher_count": TeacherProfile.objects.filter(
                status="PENDING"
            ).count(),
            "pending_leave_count": LeaveRequest.objects.filter(
                status="PENDING"
            ).count(),
        }

        return render(
            request, "admin_dashboard/activate_approved_teachers.html", context
        )

    def post(self, request):
        # Get all teachers with APPROVED status
        approved_teachers = TeacherProfile.objects.filter(status="APPROVED")
        count = approved_teachers.count()

        # Update all to ACTIVE
        approved_teachers.update(status="ACTIVE")

        messages.success(
            request, f"Successfully activated {count} previously approved teachers."
        )
        return redirect("admin_dashboard:teachers")


class AdminDashboardHomeView(AdminAccessMixin, View):
    template_name = "admin_dashboard/home.html"

    def get(self, request):
        # Get dashboard stats
        today = timezone.now().date()
        current_month = timezone.now().month
        current_year = timezone.now().year

        # Student stats
        total_students = CustomUser.objects.filter(role="student").count()
        active_students = StudentProfile.objects.filter(status="ACTIVE").count()
        pending_demos = StudentProfile.objects.filter(status="DEMO_PENDING").count()

        # Teacher stats
        total_teachers = CustomUser.objects.filter(role="teacher").count()
        active_teachers = TeacherProfile.objects.filter(status="ACTIVE").count()
        pending_approvals = TeacherProfile.objects.filter(status="PENDING").count()

        # Class stats
        today_classes = Class.objects.filter(start_time__date=today).count()
        completed_classes = Class.objects.filter(status="COMPLETED").count()

        # Monthly classes
        month_classes = Class.objects.filter(
            start_time__month=current_month, start_time__year=current_year
        ).count()

        # Financial stats
        month_earnings = (
            Payment.objects.filter(
                status="COMPLETED",
                payment_date__month=current_month,
                payment_date__year=current_year,
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        # Pending tasks
        pending_demos = StudentProfile.objects.filter(status="DEMO_PENDING").count()
        pending_teacher_approvals = TeacherProfile.objects.filter(
            status="PENDING"
        ).count()
        pending_leave_requests = LeaveRequest.objects.filter(status="PENDING").count()

        context = {
            "total_students": total_students,
            "active_students": active_students,
            "pending_demos": pending_demos,
            "total_teachers": total_teachers,
            "active_teachers": active_teachers,
            "pending_approvals": pending_approvals,
            "today_classes": today_classes,
            "completed_classes": completed_classes,
            "month_classes": month_classes,
            "month_earnings": month_earnings,
            "pending_demo_count": pending_demos,
            "pending_teacher_count": pending_teacher_approvals,
            "pending_leave_count": pending_leave_requests,
        }

        return render(request, self.template_name, context)


class StudentListView(AdminAccessMixin, View):
    template_name = "admin_dashboard/student_list.html"

    def get(self, request):
        # Get filter parameters
        status = request.GET.get("status", "")
        grade = request.GET.get("grade", "")
        board = request.GET.get("board", "")
        search = request.GET.get("search", "")

        # Base queryset
        students = StudentProfile.objects.select_related("user", "grade", "board").all()

        # Apply filters
        if status:
            students = students.filter(status=status)

        if grade:
            students = students.filter(grade_id=grade)

        if board:
            students = students.filter(board_id=board)

        if search:
            students = students.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
            )

        # Get filter options
        status_choices = StudentProfile.STUDENT_STATUS
        grades = Grade.objects.filter(is_active=True)
        boards = Board.objects.filter(is_active=True)

        context = {
            "students": students,
            "status_choices": status_choices,
            "grades": grades,
            "boards": boards,
            "current_status": status,
            "current_grade": grade,
            "current_board": board,
            "search": search,
        }

        return render(request, self.template_name, context)


class StudentDetailView(AdminAccessMixin, View):
    template_name = "admin_dashboard/student_detail.html"

    def get(self, request, student_id):
        student_profile = get_object_or_404(StudentProfile, id=student_id)
        student = student_profile.user

        # Get student classes
        upcoming_classes = Class.objects.filter(
            student=student,
            start_time__gte=timezone.now(),
            status__in=["SCHEDULED", "IN_PROGRESS"],
        ).order_by("start_time")

        past_classes = Class.objects.filter(
            student=student, end_time__lt=timezone.now()
        ).order_by("-start_time")[:10]

        # Get payments
        payments = Payment.objects.filter(student=student).order_by("-created_at")[:5]

        # Get student availability
        availabilities = Availability.objects.filter(user=student).order_by(
            "day_of_week", "start_time"
        )
        pending_demos = StudentProfile.objects.filter(status="DEMO_PENDING").count()
        pending_teacher_approvals = TeacherProfile.objects.filter(
            status="PENDING"
        ).count()
        pending_leave_requests = LeaveRequest.objects.filter(status="PENDING").count()

        context = {
            "profile": student_profile,
            "student": student,
            "upcoming_classes": upcoming_classes,
            "past_classes": past_classes,
            "payments": payments,
            "availabilities": availabilities,
            "pending_demo_count": pending_demos,
            "pending_teacher_count": pending_teacher_approvals,
            "pending_leave_count": pending_leave_requests,
        }

        return render(request, self.template_name, context)


class TeacherListView(AdminAccessMixin, View):
    template_name = "admin_dashboard/teacher_list.html"

    def get(self, request):
        # Get filter parameters
        status = request.GET.get("status", "")
        subject = request.GET.get("subject", "")
        search = request.GET.get("search", "")

        # Base queryset
        teachers = TeacherProfile.objects.select_related("user").all()

        # Apply filters
        if status:
            teachers = teachers.filter(status=status)

        if subject:
            teachers = teachers.filter(subjects__id=subject)

        if search:
            teachers = teachers.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
            )

        # Get filter options
        status_choices = TeacherProfile.TEACHER_STATUS
        subjects = Subject.objects.filter(is_active=True)

        context = {
            "teachers": teachers,
            "status_choices": status_choices,
            "subjects": subjects,
            "current_status": status,
            "current_subject": subject,
            "search": search,
        }

        return render(request, self.template_name, context)


class TeacherDetailView(AdminAccessMixin, View):
    template_name = "admin_dashboard/teacher_detail.html"

    def get(self, request, teacher_id):
        teacher_profile = get_object_or_404(TeacherProfile, id=teacher_id)
        teacher = teacher_profile.user

        # Get teacher classes
        upcoming_classes = Class.objects.filter(
            teacher=teacher,
            start_time__gte=timezone.now(),
            status__in=["SCHEDULED", "IN_PROGRESS"],
        ).order_by("start_time")

        past_classes = Class.objects.filter(
            teacher=teacher, end_time__lt=timezone.now()
        ).order_by("-start_time")[:10]

        # Get earnings
        earnings = TeacherEarning.objects.filter(teacher=teacher).order_by(
            "-month_year"
        )[:6]

        # Get teacher availability
        availabilities = Availability.objects.filter(user=teacher).order_by(
            "day_of_week", "start_time"
        )

        # Get pending leave requests
        leave_requests = LeaveRequest.objects.filter(user=teacher).order_by(
            "-created_at"
        )[:5]

        context = {
            "profile": teacher_profile,
            "teacher": teacher,
            "upcoming_classes": upcoming_classes,
            "past_classes": past_classes,
            "earnings": earnings,
            "availabilities": availabilities,
            "leave_requests": leave_requests,
        }

        return render(request, self.template_name, context)


class TeacherApprovalView(AdminAccessMixin, View):
    def post(self, request, teacher_id):
        teacher_profile = get_object_or_404(TeacherProfile, id=teacher_id)

        action = request.POST.get("action")

        if action == "approve":
            teacher_profile.status = "ACTIVE"
            messages.success(
                request,
                f"{teacher_profile.user.get_full_name()}'s profile has been approved and activated",
            )

            # Send WhatsApp notification
            WhatsAppService.send_template_message(
                teacher_profile.user,
                "TEACHER_APPROVAL",
                {"teacher_name": teacher_profile.user.get_full_name()},
            )

        elif action == "reject":
            teacher_profile.status = "REJECTED"
            messages.success(
                request,
                f"{teacher_profile.user.get_full_name()}'s profile has been rejected.",
            )

        teacher_profile.save()

        return redirect("admin_dashboard:teacher_detail", teacher_id=teacher_id)


class DemoPendingListView(AdminAccessMixin, View):
    template_name = "admin_dashboard/demo_pending_list.html"

    def get(self, request):
        # Get students with pending demo
        pending_demos = StudentProfile.objects.filter(
            status="DEMO_PENDING"
        ).select_related("user", "grade", "board")

        context = {
            "pending_demos": pending_demos,
        }

        return render(request, self.template_name, context)


class ScheduleDemoView(AdminAccessMixin, View):
    template_name = "admin_dashboard/schedule_demo.html"

    def get(self, request, student_id):
        student_profile = get_object_or_404(
            StudentProfile, id=student_id, status="DEMO_PENDING"
        )
        student = student_profile.user

        # Get student's selected subjects
        subjects = student_profile.selected_subjects.all()

        # Get student's availability
        student_availability = Availability.objects.filter(user=student).order_by(
            "day_of_week", "start_time"
        )

        # Get eligible teachers
        eligible_teachers = TeacherProfile.objects.filter(
            status="ACTIVE", subjects__in=subjects
        ).distinct()

        context = {
            "profile": student_profile,
            "student": student,
            "subjects": subjects,
            "availability": student_availability,
            "eligible_teachers": eligible_teachers,
        }

        return render(request, self.template_name, context)

    def post(self, request, student_id):
        student_profile = get_object_or_404(
            StudentProfile, id=student_id, status="DEMO_PENDING"
        )
        student = student_profile.user

        # Get form data
        subject_id = request.POST.get("subject")
        teacher_id = request.POST.get("teacher")
        date = request.POST.get("date")
        start_time = request.POST.get("start_time")
        duration = int(request.POST.get("duration", 60))

        # Validate data
        if not (subject_id and teacher_id and date and start_time):
            messages.error(request, "All fields are required.")
            return redirect("admin_dashboard:schedule_demo", student_id=student_id)

        try:
            subject = Subject.objects.get(id=subject_id)
            teacher = CustomUser.objects.get(id=teacher_id, role="teacher")

            # Parse date and time
            start_datetime = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            end_datetime = start_datetime + timedelta(minutes=duration)

            # Create the class
            demo_class = Class.objects.create(
                student=student,
                teacher=teacher,
                subject=subject,
                start_time=start_datetime,
                end_time=end_datetime,
                status="SCHEDULED",
                is_demo=True,
            )

            # Create Google Meet link
            GoogleMeetService.create_real_meeting(demo_class)

            # Update student status
            student_profile.status = "DEMO_SCHEDULED"
            student_profile.save()

            # Send notifications
            #WhatsAppService.send_demo_scheduled_notification(demo_class)

            messages.success(
                request,
                f"Demo class scheduled successfully for {student.get_full_name()}.",
            )
            return redirect(
                "admin_dashboard:student_detail", student_id=student_profile.id
            )

        except Exception as e:
            messages.error(request, f"Error scheduling demo: {str(e)}")
            return redirect("admin_dashboard:schedule_demo", student_id=student_id)


class ClassSchedulingView(AdminAccessMixin, View):
    template_name = "admin_dashboard/class_scheduling.html"

    def get(self, request, student_id):
        student_profile = get_object_or_404(
            StudentProfile, id=student_id, status__in=["DEMO_ACCEPTED", "ACTIVE"]
        )
        student = student_profile.user

        # Get month and year for scheduling
        current_month = timezone.now().month
        current_year = timezone.now().year

        month = int(request.GET.get("month", current_month))
        year = int(request.GET.get("year", current_year))

        # Get days in month
        _, days_in_month = calendar.monthrange(year, month)
        month_start = datetime(year, month, 1).date()
        month_end = datetime(year, month, days_in_month).date()

        # Get selected subjects
        subjects = student_profile.selected_subjects.all()

        # Get student's availability
        student_availability = Availability.objects.filter(user=student).order_by(
            "day_of_week", "start_time"
        )

        # Get eligible teachers
        eligible_teachers = {}
        for subject in subjects:
            subject_teachers = TeacherProfile.objects.filter(
                status="ACTIVE", subjects=subject
            ).select_related("user")
            eligible_teachers[subject.id] = subject_teachers

        # Get existing scheduled classes
        existing_classes = Class.objects.filter(
            student=student,
            start_time__date__gte=month_start,
            start_time__date__lte=month_end,
        ).order_by("start_time")

        context = {
            "profile": student_profile,
            "student": student,
            "subjects": subjects,
            "availability": student_availability,
            "eligible_teachers": eligible_teachers,
            "existing_classes": existing_classes,
            "month": month,
            "year": year,
            "days_in_month": days_in_month,
            "month_name": calendar.month_name[month],
        }

        return render(request, self.template_name, context)

    def post(self, request, student_id):
        student_profile = get_object_or_404(
            StudentProfile, id=student_id, status__in=["DEMO_ACCEPTED", "ACTIVE"]
        )
        student = student_profile.user

        # Get form data
        month = int(request.POST.get("month"))
        year = int(request.POST.get("year"))

        # Process scheduled classes
        class_count = int(request.POST.get("class_count", 0))

        for i in range(class_count):
            subject_id = request.POST.get(f"subject_{i}")
            teacher_id = request.POST.get(f"teacher_{i}")
            date = request.POST.get(f"date_{i}")
            start_time = request.POST.get(f"start_time_{i}")
            duration = int(request.POST.get(f"duration_{i}", 60))

            if subject_id and teacher_id and date and start_time:
                try:
                    subject = Subject.objects.get(id=subject_id)
                    teacher = CustomUser.objects.get(id=teacher_id, role="teacher")

                    # Parse date and time
                    start_datetime = datetime.strptime(
                        f"{date} {start_time}", "%Y-%m-%d %H:%M"
                    )
                    end_datetime = start_datetime + timedelta(minutes=duration)

                    # Create the class
                    class_obj = Class.objects.create(
                        student=student,
                        teacher=teacher,
                        subject=subject,
                        start_time=start_datetime,
                        end_time=end_datetime,
                        status="SCHEDULED",
                        is_demo=False,
                    )

                    # Create Google Meet link
                    GoogleMeetService.create_real_meeting(class_obj)

                except Exception as e:
                    messages.error(request, f"Error scheduling class: {str(e)}")

        # Create payment entry if student accepts demo
        if student_profile.status == "DEMO_ACCEPTED":
            # Calculate amount based on pricing rules
            total_amount = 0
            month_date = datetime(year, month, 1).date()

            for subject in student_profile.selected_subjects.all():
                try:
                    pricing = PricingRule.objects.get(
                        grade=student_profile.grade,
                        board=student_profile.board,
                        subject=subject,
                        is_active=True,
                    )
                    # Calculate based on number of classes
                    subject_classes = Class.objects.filter(
                        student=student,
                        subject=subject,
                        start_time__month=month,
                        start_time__year=year,
                        is_demo=False,
                    ).count()

                    subject_amount = pricing.price_per_session * subject_classes
                    total_amount += subject_amount

                except PricingRule.DoesNotExist:
                    # Default pricing if rule not found
                    subject_classes = Class.objects.filter(
                        student=student,
                        subject=subject,
                        start_time__month=month,
                        start_time__year=year,
                        is_demo=False,
                    ).count()

                    subject_amount = 500 * subject_classes  # Default price
                    total_amount += subject_amount

            # Create payment entry
            if total_amount > 0:
                Payment.objects.create(
                    student=student,
                    amount=total_amount,
                    month_year=month_date,
                    status="PENDING",
                )

        # Update student status
        if student_profile.status == "DEMO_ACCEPTED":
            student_profile.status = "ACTIVE"
            student_profile.save()

            messages.success(
                request,
                f"Classes scheduled and payment created for {student.get_full_name()}.",
            )
        else:
            messages.success(
                request, f"Classes scheduled for {student.get_full_name()}."
            )

        return redirect("admin_dashboard:student_detail", student_id=student_profile.id)


class LeaveRequestsView(AdminAccessMixin, View):
    template_name = "admin_dashboard/leave_requests.html"

    def get(self, request):
        # Get filter parameters
        status = request.GET.get("status", "PENDING")

        # Base queryset
        leave_requests = LeaveRequest.objects.select_related("user").all()

        # Apply filters
        if status:
            leave_requests = leave_requests.filter(status=status)

        context = {
            "leave_requests": leave_requests,
            "current_status": status,
        }

        return render(request, self.template_name, context)


class LeaveRequestActionView(AdminAccessMixin, View):
    def post(self, request, leave_id):
        leave_request = get_object_or_404(LeaveRequest, id=leave_id)

        action = request.POST.get("action")
        comments = request.POST.get("comments", "")

        if action == "approve":
            leave_request.approve(request.user, comments)
            messages.success(request, "Leave request approved.")
        elif action == "reject":
            leave_request.reject(request.user, comments)
            messages.success(request, "Leave request rejected.")

        return redirect("admin_dashboard:leave_requests")


class PaymentsView(AdminAccessMixin, View):
    template_name = "admin_dashboard/payments.html"

    def get(self, request):
        # Get filter parameters
        status = request.GET.get("status", "")
        month = request.GET.get("month", timezone.now().month)
        year = request.GET.get("year", timezone.now().year)

        # Base queryset
        payments = Payment.objects.select_related("student").all()

        # Apply filters
        if status:
            payments = payments.filter(status=status)

        if month and year:
            payments = payments.filter(month_year__month=month, month_year__year=year)

        # Get stats
        total_amount = (
            payments.filter(status="COMPLETED").aggregate(total=Sum("amount"))["total"]
            or 0
        )
        pending_amount = (
            payments.filter(status__in=["PENDING", "INITIATED"]).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        # Get months and years for filter dropdown
        months = [(i, calendar.month_name[i]) for i in range(1, 13)]
        current_year = timezone.now().year
        years = range(current_year - 2, current_year + 1)

        # Enhance payment data with subject information
        payment_subject_data = {}
        for payment in payments:
            try:
                student_profile = payment.student.student_profile
                selected_subjects = student_profile.selected_subjects.all()
                
                # Get subject pricing details
                subject_details = []
                for subject in selected_subjects:
                    try:
                        pricing_rule = PricingRule.objects.get(
                            subject=subject,
                            grade=student_profile.grade,
                            board=student_profile.board,
                            is_active=True
                        )
                        
                        # Calculate monthly cost (price per session × 3 classes/week × 4 weeks)
                        monthly_cost = pricing_rule.price_per_session * 12
                        
                        subject_details.append({
                            'name': subject.name,
                            'price_per_session': pricing_rule.price_per_session,
                            'monthly_cost': monthly_cost
                        })
                    except PricingRule.DoesNotExist:
                        subject_details.append({
                            'name': subject.name,
                            'price_per_session': "Not set",
                            'monthly_cost': "Not set"
                        })
                
                payment_subject_data[payment.id] = {
                    'subjects': subject_details,
                    'profile': student_profile
                }
            except Exception as e:
                # If student profile doesn't exist or other error
                payment_subject_data[payment.id] = {
                    'subjects': [],
                    'profile': None
                }

        context = {
            "payments": payments,
            "payment_subject_data": payment_subject_data,
            "status_choices": Payment.PAYMENT_STATUS,
            "current_status": status,
            "current_month": month,
            "current_year": year,
            "total_amount": total_amount,
            "pending_amount": pending_amount,
            "months": months,
            "years": years,
            "now": timezone.now(),
        }

        return render(request, self.template_name, context)

    def post(self, request):
        """Process payment actions from admin."""
        action = request.POST.get("action")
        payment_id = request.POST.get("payment_id")
        
        if not payment_id:
            messages.error(request, "Payment ID is required.")
            return redirect("admin_dashboard:payments")
        
        try:
            payment = Payment.objects.get(id=payment_id)
            
            if action == "mark_paid":
                payment_method = request.POST.get("payment_method")
                transaction_id = request.POST.get("transaction_id", "")
                payment_date_str = request.POST.get("payment_date")
                notes = request.POST.get("notes", "")
                
                try:
                    payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()
                except:
                    payment_date = timezone.now().date()
                
                # Mark payment as completed
                payment.status = "COMPLETED"
                payment.payment_method = payment_method
                payment.transaction_id = transaction_id
                payment.payment_date = payment_date
                payment.notes = notes
                payment.save()
                
                # Update student status if needed
                student_profile = payment.student.student_profile
                if student_profile.status == "DEMO_ACCEPTED":
                    student_profile.status = "ACTIVE"
                    student_profile.save()
                
                messages.success(request, f"Payment #{payment.id} marked as paid successfully.")
            
            elif action == "mark_completed":
                # For initiated payments that need to be marked as completed
                payment.status = "COMPLETED"
                payment.payment_date = timezone.now().date()
                payment.save()
                
                # Update student status if needed
                student_profile = payment.student.student_profile
                if student_profile.status == "DEMO_ACCEPTED":
                    student_profile.status = "ACTIVE"
                    student_profile.save()
                
                messages.success(request, f"Payment #{payment.id} marked as completed successfully.")
        
        except Payment.DoesNotExist:
            messages.error(request, "Payment not found.")
            
        except Exception as e:
            messages.error(request, f"Error processing payment: {str(e)}")
        
        return redirect("admin_dashboard:payments")

class TeacherEarningsView(AdminAccessMixin, View):
    template_name = "admin_dashboard/teacher_earnings.html"

    def get(self, request):
        # Get filter parameters
        status = request.GET.get("status", "")
        month = request.GET.get("month", timezone.now().month)
        year = request.GET.get("year", timezone.now().year)

        # Base queryset
        earnings = TeacherEarning.objects.select_related("teacher").all()

        # Apply filters
        if status:
            earnings = earnings.filter(payment_status=status)

        if month and year:
            earnings = earnings.filter(month_year__month=month, month_year__year=year)

        # Get stats
        total_amount = earnings.aggregate(total=Sum("amount"))["total"] or 0
        pending_amount = (
            earnings.filter(payment_status="PENDING").aggregate(total=Sum("amount"))[
                "total"
            ]
            or 0
        )

        context = {
            "earnings": earnings,
            "status_choices": TeacherEarning.PAYMENT_STATUS,
            "current_status": status,
            "current_month": month,
            "current_year": year,
            "total_amount": total_amount,
            "pending_amount": pending_amount,
        }

        return render(request, self.template_name, context)


class ProcessTeacherPaymentView(AdminAccessMixin, View):
    def post(self, request, earning_id):
        earning = get_object_or_404(
            TeacherEarning, id=earning_id, payment_status="PENDING"
        )

        payment_reference = request.POST.get("payment_reference")
        payment_date = request.POST.get("payment_date", timezone.now().date())
        notes = request.POST.get("notes", "")

        if not payment_reference:
            messages.error(request, "Payment reference is required.")
            return redirect("admin_dashboard:teacher_earnings")

        try:
            if payment_date:
                payment_date = datetime.strptime(payment_date, "%Y-%m-%d").date()
            else:
                payment_date = timezone.now().date()

            earning.mark_as_processed(payment_reference, payment_date, notes)
            messages.success(
                request, f"Payment processed for {earning.teacher.get_full_name()}."
            )

        except Exception as e:
            messages.error(request, f"Error processing payment: {str(e)}")

        return redirect("admin_dashboard:teacher_earnings")

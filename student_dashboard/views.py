from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from accounts.models import StudentProfile
from common.models import Subject, Grade, Board
from scheduling.models import Availability, Class
from payments.models import Payment
from payments.services import PayUService


class StudentAccessMixin(LoginRequiredMixin):
    """Mixin to ensure only students can access a view."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_student:
            messages.error(request, "Access denied. Student account required.")
            return redirect("landing:home")
        return super().dispatch(request, *args, **kwargs)


class StudentDashboardHomeView(StudentAccessMixin, View):
    template_name = "student_dashboard/home.html"

    def get(self, request):
        # Get student profile
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            profile = StudentProfile.objects.create(user=request.user)

        # Get upcoming classes
        upcoming_classes = Class.objects.filter(
            student=request.user,
            start_time__gte=timezone.now(),
            status__in=["SCHEDULED", "IN_PROGRESS"],
        ).order_by("start_time")[:5]

        # Get recent classes
        recent_classes = Class.objects.filter(
            student=request.user, end_time__lt=timezone.now(), status="COMPLETED"
        ).order_by("-start_time")[:5]

        # Get recent payments
        recent_payments = Payment.objects.filter(student=request.user).order_by(
            "-created_at"
        )[:3]

        context = {
            "profile": profile,
            "upcoming_classes": upcoming_classes,
            "recent_classes": recent_classes,
            "recent_payments": recent_payments,
        }

        return render(request, self.template_name, context)


class StudentProfileView(StudentAccessMixin, View):
    template_name = "student_dashboard/profile.html"

    def get(self, request):
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            profile = StudentProfile.objects.create(user=request.user)

        # Get available grades and boards
        grades = Grade.objects.filter(is_active=True)
        boards = Board.objects.filter(is_active=True)
        print(profile.user.phone_number)
        context = {
            "profile": profile,
            "grades": grades,
            "boards": boards,
        }

        return render(request, self.template_name, context)

    def post(self, request):
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            profile = StudentProfile.objects.create(user=request.user)

        # Check which form was submitted
        form_type = request.POST.get("form_type")

        if form_type == "personal_info":
            # Update personal information
            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()


            # Update user directly in the database to ensure it's saved
            from django.contrib.auth import get_user_model

            User = get_user_model()
            User.objects.filter(id=request.user.id).update(
                first_name=first_name, last_name=last_name
            )

            # Refresh the user object from the database
            request.user.refresh_from_db()

            messages.success(request, "Personal information updated successfully.")

        else:
            # Handle education details form
            grade_id = request.POST.get("grade")
            board_id = request.POST.get("board")

            if grade_id and board_id:
                # Print debug info

                # Update profile
                profile.grade_id = grade_id
                profile.board_id = board_id
                profile.save()

                # Update status if needed
                if profile.status == "NEW":
                    profile.update_status("NEW")

                messages.success(request, "Education details updated successfully.")
            else:
                messages.error(request, "Please select both grade and board.")

        return redirect("student_dashboard:profile")


class SubjectSelectionView(StudentAccessMixin, View):
    template_name = "student_dashboard/subject_selection.html"

    def get(self, request):
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            messages.error(request, "Please complete your profile first.")
            return redirect("student_dashboard:profile")

        # Check if grade and board are set
        if not profile.grade or not profile.board:
            messages.error(request, "Please select your grade and board first.")
            return redirect("student_dashboard:profile")

        # Get subjects
        subjects = Subject.objects.filter(is_active=True)

        # Get selected subjects
        selected_subjects = profile.selected_subjects.all()

        context = {
            "profile": profile,
            "subjects": subjects,
            "selected_subjects": selected_subjects,
        }

        return render(request, self.template_name, context)

    def post(self, request):
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            messages.error(request, "Please complete your profile first.")
            return redirect("student_dashboard:profile")

        # Get selected subject IDs
        subject_ids = request.POST.getlist("subjects")

        if not subject_ids:
            messages.error(request, "Please select at least one subject.")
            return redirect("student_dashboard:subject_selection")

        # Update selected subjects
        subjects = Subject.objects.filter(id__in=subject_ids)
        profile.selected_subjects.set(subjects)

        # Update status
        if profile.status == "NEW" or profile.status == "PRICING_REQUESTED":
            profile.update_status("PRICING_REQUESTED")

        messages.success(request, "Subject selection updated successfully.")
        return redirect("student_dashboard:availability")


# Add these modified methods to your views.py file


class AvailabilitySetupView(StudentAccessMixin, View):
    template_name = "student_dashboard/availability_setup.html"

    def get(self, request):
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            messages.error(request, "Please complete your profile first.")
            return redirect("student_dashboard:profile")

        # Check if subjects are selected
        if profile.selected_subjects.count() == 0:
            messages.error(request, "Please select subjects first.")
            return redirect("student_dashboard:subject_selection")

        # Get existing availability slots
        availabilities = Availability.objects.filter(user=request.user).order_by(
            "day_of_week", "start_time"
        )

        context = {
            "profile": profile,
            "availabilities": availabilities,
            "days_of_week": dict(Availability.DAYS_OF_WEEK),
        }

        return render(request, self.template_name, context)

    def post(self, request):
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            messages.error(request, "Please complete your profile first.")
            return redirect("student_dashboard:profile")

        # Process availability form
        days = request.POST.getlist("day")
        start_times = request.POST.getlist("start_time")
        end_times = request.POST.getlist("end_time")
        slot_ids = request.POST.getlist("slot_id")

        # First, delete all existing availability slots
        Availability.objects.filter(user=request.user).delete()

        # Add new availability slots
        created_slots = []
        for i in range(len(days)):
            if i < len(start_times) and i < len(end_times):
                slot = Availability.objects.create(
                    user=request.user,
                    day_of_week=int(days[i]),
                    start_time=start_times[i],
                    end_time=end_times[i],
                    is_recurring=True,
                )
                created_slots.append(slot.id)

        # Force database commit to ensure all changes are saved
        from django.db import transaction
        transaction.commit()

        # Check if minimum 3 slots are provided
        current_slots = Availability.objects.filter(user=request.user)
        slot_count = current_slots.count()

        if slot_count >= 3:
            # Update status
            if profile.status == "PRICING_REQUESTED":
                profile.update_status("AVAILABILITY_SET")
            
            messages.success(request, "Availability settings saved successfully.")
            return redirect("student_dashboard:demo_request")
        else:
            messages.error(
                request,
                f"Please provide at least 3 availability slots per week. Currently you have {slot_count}.",
            )
            return redirect("student_dashboard:availability")
from scheduling.models import Availability, Class


class DemoRequestView(StudentAccessMixin, View):
    template_name = "student_dashboard/demo_request.html"

    def get(self, request):
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            messages.error(request, "Please complete your profile first.")
            return redirect("student_dashboard:profile")

        # Check if availability is set - with enhanced debugging
        availabilities = Availability.objects.filter(user=request.user)
        availability_count = availabilities.count()

        if availability_count < 3:
            messages.error(
                request,
                f"Please set your availability first (minimum 3 slots). Currently found: {availability_count}",
            )
            return redirect("student_dashboard:availability")

        # Get selected subjects
        subjects = profile.selected_subjects.all()

        # Check if demo is already scheduled or requested
        demo_class = Class.objects.filter(
            student=request.user, is_demo=True, status__in=["SCHEDULED", "IN_PROGRESS"]
        ).first()


        context = {
            "profile": profile,
            "subjects": subjects,
            "demo_class": demo_class,
            "Availability": availability_count,
        }
        

        return render(request, self.template_name, context)

    def post(self, request):
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            messages.error(request, "Please complete your profile first.")
            return redirect("student_dashboard:profile")

        # Get selected subject
        subject_id = request.POST.get("subject")

        if not subject_id:
            messages.error(request, "Please select a subject for the demo class.")
            return redirect("student_dashboard:demo_request")

        subject = get_object_or_404(Subject, id=subject_id)

        # Check if demo is already scheduled
        existing_demo = Class.objects.filter(
            student=request.user, is_demo=True, status__in=["SCHEDULED", "IN_PROGRESS"]
        ).exists()

        if existing_demo:
            messages.error(request, "You already have a demo class scheduled.")
            return redirect("student_dashboard:classes")

        # Update status to demo pending
        profile.update_status("DEMO_PENDING")

        messages.success(
            request,
            f"Demo class for {subject.name} requested successfully. Admin will schedule it based on your availability.",
        )
        return redirect("student_dashboard:classes")


class ClassesListView(StudentAccessMixin, View):
    template_name = "student_dashboard/classes.html"

    def get(self, request):
        # Get upcoming classes
        upcoming_classes = Class.objects.filter(
            student=request.user,
            start_time__gte=timezone.now(),
            status__in=["SCHEDULED", "IN_PROGRESS"],
        ).order_by("start_time")

        # Get past classes
        past_classes = Class.objects.filter(
            student=request.user, end_time__lt=timezone.now()
        ).order_by("-start_time")

        context = {
            "upcoming_classes": upcoming_classes,
            "past_classes": past_classes,
            "meetings": Class.meeting_link,
        }

        return render(request, self.template_name, context)


class ClassDetailView(StudentAccessMixin, View):
    template_name = "student_dashboard/class_detail.html"

    def get(self, request, class_id):
        class_obj = get_object_or_404(Class, id=class_id, student=request.user)

        context = {
            "class": class_obj,
            "can_join": class_obj.can_join(),
            "is_demo": class_obj.is_demo,
        }

        return render(request, self.template_name, context)


class JoinClassView(StudentAccessMixin, View):
    template_name = "student_dashboard/join_class.html"

    def get(self, request, class_id):
        class_obj = get_object_or_404(Class, id=class_id, student=request.user)

        # Check if class can be joined
        if not class_obj.can_join():
            messages.error(request, "This class is not available to join right now.")
            return redirect("student_dashboard:class_detail", class_id=class_id)

        # If class is in progress, update status
        if class_obj.is_ongoing() and class_obj.status == "SCHEDULED":
            class_obj.status = "IN_PROGRESS"
            class_obj.save()

        context = {
            "class": class_obj,
        }

        return render(request, self.template_name, context)


class PaymentsView(StudentAccessMixin, View):
    template_name = "student_dashboard/payments.html"

    def get(self, request):
        # Get all payments
        payments = Payment.objects.filter(student=request.user).order_by("-created_at")

        # Get pending payment if exists
        pending_payment = payments.filter(status__in=["PENDING", "INITIATED"]).first()

        context = {
            "payments": payments,
            "pending_payment": pending_payment,
        }

        return render(request, self.template_name, context)


class InitiatePaymentView(StudentAccessMixin, View):
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
            "student_dashboard/payment_initiate.html",
            {
                "payment": payment,
                "params": payment_request["params"],
                "payu_url": payment_request["url"],
            },
        )


class DemoFeedbackView(StudentAccessMixin, View):
    template_name = "student_dashboard/demo_feedback.html"

    def get(self, request, class_id):
        class_obj = get_object_or_404(
            Class,
            id=class_id,
            student=request.user,
            is_demo=True,
            status__in=["COMPLETED", "MISSED"],
        )

        context = {
            "class": class_obj,
        }

        return render(request, self.template_name, context)

    def post(self, request, class_id):
        class_obj = get_object_or_404(
            Class, id=class_id, student=request.user, is_demo=True
        )

        # Process feedback
        rating = request.POST.get("rating")
        feedback = request.POST.get("feedback")
        accept_demo = request.POST.get("accept_demo") == "yes"

        # Update class notes with feedback
        class_obj.notes = f"Rating: {rating}/5\n\nFeedback: {feedback}"
        class_obj.save()

        # Update student status based on acceptance
        profile = request.user.student_profile

        if accept_demo:
            profile.update_status("DEMO_ACCEPTED")
            messages.success(
                request,
                "Great! You've accepted the demo class. We'll now create your regular class schedule.",
            )
        else:
            # Keep status as is or update to request another demo
            messages.info(
                request,
                "Thank you for your feedback. We'll continue improving our services.",
            )

        return redirect("student_dashboard:classes")

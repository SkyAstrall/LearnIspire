from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta

from accounts.models import TeacherProfile
from common.models import Subject
from scheduling.models import Availability, Class, ClassMaterial, LeaveRequest
from payments.models import TeacherEarning


class TeacherAccessMixin(LoginRequiredMixin):
    """Mixin to ensure only teachers can access a view."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_teacher:
            messages.error(request, "Access denied. Teacher account required.")
            return redirect("landing:home")
        return super().dispatch(request, *args, **kwargs)


class TeacherDashboardHomeView(TeacherAccessMixin, View):
    template_name = "teacher_dashboard/home.html"

    def get(self, request):
        # Get teacher profile
        try:
            profile = request.user.teacher_profile
        except TeacherProfile.DoesNotExist:
            profile = TeacherProfile.objects.create(user=request.user)

        # Get upcoming classes
        today = timezone.now().date()
        upcoming_classes = Class.objects.filter(
            teacher=request.user,
            start_time__date=today,
            status__in=["SCHEDULED", "IN_PROGRESS"],
        ).order_by("start_time")

        # Get weekly schedule
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        weekly_classes = Class.objects.filter(
            teacher=request.user,
            start_time__date__gte=week_start,
            start_time__date__lte=week_end,
        ).order_by("start_time")

        # Get today's completed classes
        completed_today = Class.objects.filter(
            teacher=request.user, start_time__date=today, status="COMPLETED"
        ).count()

        # Get pending leave requests
        pending_leaves = LeaveRequest.objects.filter(
            user=request.user, status="PENDING"
        )

        # Get monthly stats
        current_month = timezone.now().month
        current_year = timezone.now().year

        monthly_classes = Class.objects.filter(
            teacher=request.user,
            start_time__month=current_month,
            start_time__year=current_year,
        )

        total_classes_month = monthly_classes.count()
        completed_classes_month = monthly_classes.filter(status="COMPLETED").count()

        # Get earnings
        current_month_date = datetime(current_year, current_month, 1).date()
        earnings = TeacherEarning.objects.filter(
            teacher=request.user,
            month_year__year=current_year,
            month_year__month=current_month,
        ).first()

        if not earnings:
            # Calculate if not exists
            earnings = TeacherEarning.calculate_for_teacher_month(
                request.user, current_month_date
            )

        context = {
            "profile": profile,
            "upcoming_classes": upcoming_classes,
            "weekly_classes": weekly_classes,
            "completed_today": completed_today,
            "pending_leaves": pending_leaves,
            "total_classes_month": total_classes_month,
            "completed_classes_month": completed_classes_month,
            "earnings": earnings,
            "week_start": week_start,
            "week_end": week_end,
        }

        return render(request, self.template_name, context)


class TeacherProfileView(TeacherAccessMixin, View):
    template_name = "teacher_dashboard/profile.html"

    def get(self, request):
        try:
            profile = request.user.teacher_profile
        except TeacherProfile.DoesNotExist:
            profile = TeacherProfile.objects.create(user=request.user)

        # Get available subjects
        subjects = Subject.objects.filter(is_active=True)

        context = {
            "profile": profile,
            "subjects": subjects,
        }

        return render(request, self.template_name, context)
    
    def post(self, request):
        try:
            profile = request.user.teacher_profile
        except TeacherProfile.DoesNotExist:
            profile = TeacherProfile.objects.create(user=request.user)

        # Update user info
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.save()

        # Update profile info
        profile.phone = request.POST.get('phone')
        profile.highest_qualification = request.POST.get('highest_qualification', '')
        profile.university = request.POST.get('university', '')
        profile.graduation_year = request.POST.get('graduation_year', None)
        profile.specialization = request.POST.get('specialization', '')
        profile.skills = request.POST.get('skills', '')
        profile.years_of_experience = request.POST.get('years_of_experience', 0)
        profile.experience = request.POST.get('experience', '')
        profile.bio = request.POST.get('bio', '')
        print(request.POST.get('phone', ''))

        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']

        # Update subjects
        selected_subjects = request.POST.getlist('subjects', [])
        profile.subjects.clear()
        for subject_id in selected_subjects:
            try:
                subject = Subject.objects.get(id=subject_id)
                profile.subjects.add(subject)
            except Subject.DoesNotExist:
                pass

        profile.save()

        messages.success(request, "Profile updated successfully.")
        return redirect('teacher_dashboard:profile')


class AvailabilitySetupView(TeacherAccessMixin, View):
    template_name = "teacher_dashboard/availability_setup.html"

    def get(self, request):
        try:
            profile = request.user.teacher_profile
        except TeacherProfile.DoesNotExist:
            profile = TeacherProfile.objects.create(user=request.user)

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
            profile = request.user.teacher_profile
        except TeacherProfile.DoesNotExist:
            profile = TeacherProfile.objects.create(user=request.user)

        # Process availability form
        days = request.POST.getlist("day")
        start_times = request.POST.getlist("start_time")
        end_times = request.POST.getlist("end_time")

        # Clear existing availability
        Availability.objects.filter(user=request.user).delete()

        # Add new availability slots
        for i in range(len(days)):
            if i < len(start_times) and i < len(end_times):
                Availability.objects.create(
                    user=request.user,
                    day_of_week=int(days[i]),
                    start_time=start_times[i],
                    end_time=end_times[i],
                    is_recurring=True,
                )

        # Check if minimum 3 slots are provided
        if Availability.objects.filter(user=request.user).count() >= 3:
            messages.success(request, "Availability settings saved successfully.")
            return redirect("teacher_dashboard:home")
        else:
            messages.error(
                request, "Please provide at least 3 availability slots per week."
            )
            return redirect("teacher_dashboard:availability")


class ClassesListView(TeacherAccessMixin, View):
    template_name = "teacher_dashboard/classes.html"

    def get(self, request):
        # Get upcoming classes
        upcoming_classes = Class.objects.filter(
            teacher=request.user,
            start_time__gte=timezone.now(),
            status__in=["SCHEDULED", "IN_PROGRESS"],
        ).order_by("start_time")

        # Get past classes
        past_classes = Class.objects.filter(
            teacher=request.user, end_time__lt=timezone.now()
        ).order_by("-start_time")

        context = {
            "upcoming_classes": upcoming_classes,
            "past_classes": past_classes,
        }

        return render(request, self.template_name, context)


class ClassDetailView(TeacherAccessMixin, View):
    template_name = "teacher_dashboard/class_detail.html"

    def get(self, request, class_id):
        class_obj = get_object_or_404(Class, id=class_id, teacher=request.user)

        # Get class materials
        materials = class_obj.materials.all()

        context = {
            "class": class_obj,
            "materials": materials,
            "can_join": class_obj.can_join(),
            "is_demo": class_obj.is_demo,
        }

        return render(request, self.template_name, context)


class JoinClassView(TeacherAccessMixin, View):
    template_name = "teacher_dashboard/join_class.html"

    def get(self, request, class_id):
        class_obj = get_object_or_404(Class, id=class_id, teacher=request.user)

        # Check if class can be joined
        if not class_obj.can_join():
            messages.error(request, "This class is not available to join right now.")
            return redirect("teacher_dashboard:class_detail", class_id=class_id)

        # If class is in progress, update status
        if class_obj.is_ongoing() and class_obj.status == "SCHEDULED":
            class_obj.status = "IN_PROGRESS"
            class_obj.save()

        context = {
            "class": class_obj,
        }

        return render(request, self.template_name, context)


class CompleteClassView(TeacherAccessMixin, View):
    template_name = "teacher_dashboard/complete_class.html"

    def get(self, request, class_id):
        class_obj = get_object_or_404(Class, id=class_id, teacher=request.user)

        # Ensure class can be marked as complete
        now = timezone.now()
        if now < class_obj.end_time:
            messages.warning(
                request,
                "This class is still in progress and cannot be marked as completed yet.",
            )
            return redirect("teacher_dashboard:class_detail", class_id=class_id)

        context = {
            "class": class_obj,
        }

        return render(request, self.template_name, context)

    def post(self, request, class_id):
        class_obj = get_object_or_404(Class, id=class_id, teacher=request.user)

        # Mark class as completed
        class_obj.status = "COMPLETED"

        # Save teacher notes
        notes = request.POST.get("notes", "")
        if notes:
            class_obj.notes = notes

        class_obj.save()

        # Handle file uploads if any
        if "material_file" in request.FILES:
            material_file = request.FILES["material_file"]
            material_title = request.POST.get("material_title", "Class Material")
            material_description = request.POST.get("material_description", "")

            ClassMaterial.objects.create(
                class_session=class_obj,
                title=material_title,
                description=material_description,
                file=material_file,
                uploaded_by=request.user,
            )

        messages.success(request, "Class marked as completed successfully.")
        return redirect("teacher_dashboard:classes")


class UploadMaterialView(TeacherAccessMixin, View):
    def post(self, request, class_id):
        class_obj = get_object_or_404(Class, id=class_id, teacher=request.user)

        if "material_file" in request.FILES:
            material_file = request.FILES["material_file"]
            material_title = request.POST.get("material_title", "Class Material")
            material_description = request.POST.get("material_description", "")

            ClassMaterial.objects.create(
                class_session=class_obj,
                title=material_title,
                description=material_description,
                file=material_file,
                uploaded_by=request.user,
            )

            messages.success(request, "Material uploaded successfully.")
        else:
            messages.error(request, "No file selected for upload.")

        return redirect("teacher_dashboard:class_detail", class_id=class_id)


class LeaveRequestView(TeacherAccessMixin, View):
    template_name = "teacher_dashboard/leave_request.html"

    def get(self, request):
        # Get all leave requests
        leave_requests = LeaveRequest.objects.filter(user=request.user).order_by(
            "-created_at"
        )

        context = {
            "leave_requests": leave_requests,
        }

        return render(request, self.template_name, context)

    def post(self, request):
        # Process leave request form
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        reason = request.POST.get("reason")

        if not (start_date and end_date and reason):
            messages.error(request, "All fields are required.")
            return redirect("teacher_dashboard:leave_request")

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

            # Validate dates
            if start_date < timezone.now().date():
                messages.error(request, "Start date cannot be in the past.")
                return redirect("teacher_dashboard:leave_request")

            if end_date < start_date:
                messages.error(request, "End date must be on or after start date.")
                return redirect("teacher_dashboard:leave_request")

            # Create leave request
            LeaveRequest.objects.create(
                user=request.user,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
                status="PENDING",
            )

            messages.success(request, "Leave request submitted successfully.")
            return redirect("teacher_dashboard:leave_request")

        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect("teacher_dashboard:leave_request")


class EarningsView(TeacherAccessMixin, View):
    template_name = "teacher_dashboard/earnings.html"

    def get(self, request):
        # Get earnings for the past 6 months
        now = timezone.now()
        earnings = []

        for i in range(6):
            month = now.month - i
            year = now.year

            if month <= 0:
                month += 12
                year -= 1

            month_date = datetime(year, month, 1).date()

            # Get or calculate earnings
            month_earnings = TeacherEarning.objects.filter(
                teacher=request.user, month_year__year=year, month_year__month=month
            ).first()

            if not month_earnings:
                month_earnings = TeacherEarning.calculate_for_teacher_month(
                    request.user, month_date
                )

            earnings.append(month_earnings)

        # Get total classes conducted
        total_classes = Class.objects.filter(
            teacher=request.user, status="COMPLETED"
        ).count()

        # Get total earnings
        total_earnings = (
            TeacherEarning.objects.filter(teacher=request.user).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        context = {
            "earnings": earnings,
            "total_classes": total_classes,
            "total_earnings": total_earnings,
        }

        return render(request, self.template_name, context)


class BankDetailsView(TeacherAccessMixin, View):
    template_name = "teacher_dashboard/bank_details.html"

    def get(self, request):
        try:
            profile = request.user.teacher_profile
        except TeacherProfile.DoesNotExist:
            profile = TeacherProfile.objects.create(user=request.user)

        context = {
            "profile": profile,
        }

        return render(request, self.template_name, context)

    def post(self, request):
        try:
            profile = request.user.teacher_profile
        except TeacherProfile.DoesNotExist:
            profile = TeacherProfile.objects.create(user=request.user)

        # Update bank details
        profile.bank_name = request.POST.get("bank_name", "")
        profile.account_number = request.POST.get("account_number", "")
        profile.ifsc_code = request.POST.get("ifsc_code", "")
        profile.account_holder_name = request.POST.get("account_holder_name", "")
        profile.branch_name = request.POST.get("branch_name", "")
        profile.save()

        messages.success(request, "Bank details updated successfully.")
        return redirect("teacher_dashboard:home")

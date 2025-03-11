from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q

from .models import Availability, Class, LeaveRequest


class AvailabilityListView(LoginRequiredMixin, View):
    template_name = "scheduling/availability_list.html"

    def get(self, request):
        availabilities = Availability.objects.filter(user=request.user).order_by(
            "day_of_week", "start_time"
        )

        context = {
            "availabilities": availabilities,
            "days_of_week": dict(Availability.DAYS_OF_WEEK),
        }

        return render(request, self.template_name, context)


class ClassListView(LoginRequiredMixin, View):
    template_name = "scheduling/class_list.html"

    def get(self, request):
        # Determine if user is a teacher or student and filter accordingly
        if request.user.is_teacher:
            upcoming_classes = Class.objects.filter(
                teacher=request.user,
                start_time__gte=timezone.now(),
                status__in=["SCHEDULED", "IN_PROGRESS"],
            ).order_by("start_time")

            past_classes = Class.objects.filter(
                teacher=request.user, end_time__lt=timezone.now()
            ).order_by("-start_time")
        else:
            upcoming_classes = Class.objects.filter(
                student=request.user,
                start_time__gte=timezone.now(),
                status__in=["SCHEDULED", "IN_PROGRESS"],
            ).order_by("start_time")

            past_classes = Class.objects.filter(
                student=request.user, end_time__lt=timezone.now()
            ).order_by("-start_time")

        context = {
            "upcoming_classes": upcoming_classes,
            "past_classes": past_classes,
        }

        return render(request, self.template_name, context)


class ClassDetailView(LoginRequiredMixin, View):
    template_name = "scheduling/class_detail.html"

    def get(self, request, class_id):
        # Check if user is involved in the class
        if request.user.is_teacher:
            class_obj = get_object_or_404(Class, id=class_id, teacher=request.user)
        else:
            class_obj = get_object_or_404(Class, id=class_id, student=request.user)

        context = {
            "class": class_obj,
            "materials": class_obj.materials.all(),
        }

        return render(request, self.template_name, context)


class LeaveRequestListView(LoginRequiredMixin, View):
    template_name = "scheduling/leave_list.html"

    def get(self, request):
        leave_requests = LeaveRequest.objects.filter(user=request.user).order_by(
            "-created_at"
        )

        context = {
            "leave_requests": leave_requests,
        }

        return render(request, self.template_name, context)


class LeaveRequestCreateView(LoginRequiredMixin, View):
    template_name = "scheduling/leave_create.html"

    def get(self, request):
        context = {}
        return render(request, self.template_name, context)

    def post(self, request):
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        reason = request.POST.get("reason")

        if not (start_date and end_date and reason):
            messages.error(request, "All fields are required.")
            return redirect("scheduling:leave_create")

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

            # Validate dates
            if start_date < timezone.now().date():
                messages.error(request, "Start date cannot be in the past.")
                return redirect("scheduling:leave_create")

            if end_date < start_date:
                messages.error(request, "End date must be on or after start date.")
                return redirect("scheduling:leave_create")

            # Create leave request
            LeaveRequest.objects.create(
                user=request.user,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
                status="PENDING",
            )

            messages.success(request, "Leave request submitted successfully.")
            return redirect("scheduling:leave_list")

        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect("scheduling:leave_create")


def check_availability(request):
    """API endpoint to check availability for scheduling."""
    if request.method == "GET":
        user_id = request.GET.get("user_id")
        date = request.GET.get("date")

        if not (user_id and date):
            return JsonResponse({"success": False, "error": "Missing parameters"})

        try:
            from accounts.models import CustomUser

            user = CustomUser.objects.get(id=user_id)
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()

            # Get day of week (0 = Monday, 6 = Sunday)
            day_of_week = date_obj.weekday()

            # Get availabilities for that day
            availabilities = Availability.objects.filter(
                user=user, day_of_week=day_of_week
            ).order_by("start_time")

            # Get existing classes for that date
            existing_classes = Class.objects.filter(
                Q(teacher=user) | Q(student=user), start_time__date=date_obj
            )

            # Format availabilities
            available_slots = []
            for avail in availabilities:
                # Check if slot is already booked
                is_available = True
                for cls in existing_classes:
                    # Convert times to comparable format
                    cls_start = cls.start_time.time()
                    cls_end = cls.end_time.time()

                    # Check for overlap
                    if (
                        (avail.start_time <= cls_start < avail.end_time)
                        or (avail.start_time < cls_end <= avail.end_time)
                        or (cls_start <= avail.start_time and cls_end >= avail.end_time)
                    ):
                        is_available = False
                        break

                if is_available:
                    available_slots.append(
                        {
                            "start_time": avail.start_time.strftime("%H:%M"),
                            "end_time": avail.end_time.strftime("%H:%M"),
                        }
                    )

            return JsonResponse(
                {
                    "success": True,
                    "date": date,
                    "day_of_week": dict(Availability.DAYS_OF_WEEK)[day_of_week],
                    "available_slots": available_slots,
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method"})

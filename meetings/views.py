from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone

from scheduling.models import Class
from .services import GoogleMeetService


class JoinMeetingView(LoginRequiredMixin, View):
    """View for joining a Google Meet session."""

    def get(self, request, class_id):
        # Check if user is involved in the class
        if request.user.is_teacher:
            class_obj = get_object_or_404(Class, id=class_id, teacher=request.user)
        else:
            class_obj = get_object_or_404(Class, id=class_id, student=request.user)

        # Check if class can be joined
        if not class_obj.can_join():
            messages.error(request, "This class is not available to join right now.")

            if request.user.is_teacher:
                return redirect("teacher_dashboard:class_detail", class_id=class_id)
            else:
                return redirect("student_dashboard:class_detail", class_id=class_id)

        # If class is in progress, update status
        if class_obj.is_ongoing() and class_obj.status == "SCHEDULED":
            class_obj.status = "IN_PROGRESS"
            class_obj.save()

        # If meeting link doesn't exist, create one
        if not class_obj.meeting_link:
            result = GoogleMeetService.create_real_meeting(class_obj)
            if not result["success"]:
                messages.error(
                    request, "Failed to create meeting link. Please try again."
                )

                if request.user.is_teacher:
                    return redirect("teacher_dashboard:class_detail", class_id=class_id)
                else:
                    return redirect("student_dashboard:class_detail", class_id=class_id)

        context = {
            "class": class_obj,
        }

        return render(request, "meetings/join.html", context)


class EndMeetingView(LoginRequiredMixin, View):
    """View for ending a meeting (for teachers only)."""

    def post(self, request, class_id):
        # Only teachers can end meetings
        if not request.user.is_teacher:
            messages.error(request, "Only teachers can end meetings.")
            return redirect("student_dashboard:class_detail", class_id=class_id)

        class_obj = get_object_or_404(Class, id=class_id, teacher=request.user)

        # Check if class is in progress
        if class_obj.status != "IN_PROGRESS":
            messages.error(request, "This class is not in progress.")
            return redirect("teacher_dashboard:class_detail", class_id=class_id)

        # Mark class as completed
        class_obj.status = "COMPLETED"
        class_obj.save()

        messages.success(request, "Class marked as completed.")
        return redirect("teacher_dashboard:class_detail", class_id=class_id)


class MeetingFeedbackView(LoginRequiredMixin, View):
    """View for providing feedback after a meeting."""

    def get(self, request, class_id):
        # Check if user is involved in the class
        if request.user.is_teacher:
            class_obj = get_object_or_404(Class, id=class_id, teacher=request.user)
            template_name = "meetings/teacher_feedback.html"
        else:
            class_obj = get_object_or_404(Class, id=class_id, student=request.user)
            template_name = "meetings/student_feedback.html"

        # Check if class is completed
        if class_obj.status != "COMPLETED":
            messages.error(
                request, "Feedback can only be provided for completed classes."
            )

            if request.user.is_teacher:
                return redirect("teacher_dashboard:class_detail", class_id=class_id)
            else:
                return redirect("student_dashboard:class_detail", class_id=class_id)

        context = {
            "class": class_obj,
        }

        return render(request, template_name, context)

    def post(self, request, class_id):
        # Check if user is involved in the class
        if request.user.is_teacher:
            class_obj = get_object_or_404(Class, id=class_id, teacher=request.user)
            redirect_url = "teacher_dashboard:class_detail"
        else:
            class_obj = get_object_or_404(Class, id=class_id, student=request.user)
            redirect_url = "student_dashboard:class_detail"

        # Process feedback
        rating = request.POST.get("rating")
        comments = request.POST.get("comments", "")

        if not rating:
            messages.error(request, "Please provide a rating.")
            return redirect("meetings:feedback", class_id=class_id)

        # Save feedback
        feedback = f"Rating: {rating}/5\n\n"
        if comments:
            feedback += f"Comments: {comments}\n\n"

        # Append to existing notes
        if class_obj.notes:
            class_obj.notes += (
                f"\n\n{request.user.get_full_name()} Feedback:\n{feedback}"
            )
        else:
            class_obj.notes = f"{request.user.get_full_name()} Feedback:\n{feedback}"

        class_obj.save()

        messages.success(request, "Feedback submitted successfully.")
        return redirect(redirect_url, class_id=class_id)

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

from common.models import Subject, Grade, Board, PricingRule


class HomeView(View):
    template_name = "landing/home.html"

    def get(self, request):
        # Get active subjects for display
        subjects = Subject.objects.filter(is_active=True)[:8]

        context = {
            "subjects": subjects,
        }

        return render(request, self.template_name, context)


class AboutView(View):
    template_name = "landing/about.html"

    def get(self, request):
        return render(request, self.template_name)


class PricingView(View):
    template_name = "landing/pricing.html"

    def get(self, request):
        # Get grades and boards
        grades = Grade.objects.filter(is_active=True)
        boards = Board.objects.filter(is_active=True)

        # Get selected grade and board from query params
        selected_grade = request.GET.get("grade")
        selected_board = request.GET.get("board")

        pricing_rules = []

        if selected_grade and selected_board:
            try:
                grade = Grade.objects.get(id=selected_grade)
                board = Board.objects.get(id=selected_board)

                # Get pricing rules for selected grade and board
                pricing_rules = PricingRule.objects.filter(
                    grade=grade, board=board, is_active=True
                ).select_related("subject")

            except (Grade.DoesNotExist, Board.DoesNotExist):
                pass

        context = {
            "grades": grades,
            "boards": boards,
            "selected_grade": selected_grade,
            "selected_board": selected_board,
            "pricing_rules": pricing_rules,
        }

        return render(request, self.template_name, context)


class ContactView(View):
    template_name = "landing/contact.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        name = request.POST.get("name")
        email = request.POST.get("email")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        if not (name and email and subject and message):
            messages.error(request, "Please fill all the fields.")
            return render(request, self.template_name)

        # Send email
        try:
            full_message = f"Name: {name}\nEmail: {email}\n\n{message}"

            send_mail(
                f"Contact Form: {subject}",
                full_message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL],  # Send to admin email
                fail_silently=False,
            )

            messages.success(
                request,
                "Your message has been sent successfully. We'll get back to you soon!",
            )
            return redirect("landing:contact")

        except Exception as e:
            messages.error(request, f"Error sending email: {str(e)}")
            return render(request, self.template_name)


class SubjectsView(View):
    template_name = "landing/subjects.html"

    def get(self, request):
        # Get all active subjects
        subjects = Subject.objects.filter(is_active=True)

        context = {
            "subjects": subjects,
        }

        return render(request, self.template_name, context)


class PrivacyPolicyView(View):
    template_name = "landing/privacy_policy.html"

    def get(self, request):
        return render(request, self.template_name)


class TermsConditionsView(View):
    template_name = "landing/terms_conditions.html"

    def get(self, request):
        return render(request, self.template_name)

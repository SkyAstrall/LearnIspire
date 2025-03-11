import random
import string
import datetime
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter
from twilio.rest import Client
from .models import PhoneVerification, CustomUser


class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        """
        Extends the default save_user method to include phone number.
        """
        user = super().save_user(request, user, form, commit=False)

        # Set role from form data if provided
        if "role" in form.cleaned_data:
            user.role = form.cleaned_data["role"]

        # Set phone number if provided
        if "phone_number" in form.cleaned_data:
            user.phone_number = form.cleaned_data["phone_number"]

        if commit:
            user.save()

            # Generate OTP for phone verification
            if user.phone_number:
                self.generate_otp(user, user.phone_number)

        return user

    def generate_otp(self, user, phone_number):
        """
        Generate a 6-digit OTP and send via WhatsApp using Twilio.
        """
        # Generate 6-digit OTP
        otp = "".join(random.choices(string.digits, k=6))
        print(otp)

        # Set expiration time (15 minutes from now)
        expires_at = timezone.now() + datetime.timedelta(minutes=15)

        # Save OTP to database
        verification = PhoneVerification(
            user=user, phone_number=phone_number, otp=otp, expires_at=expires_at
        )
        verification.save()

        # Send OTP via WhatsApp using Twilio
        self.send_whatsapp_otp(phone_number, otp)

        return otp

    def send_whatsapp_otp(self, phone_number, otp):
        """
        Send OTP via WhatsApp using Twilio.
        """
        try:
            print(otp)
            # Initialize Twilio client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

            # Format message
            message_body = f"Your LearnIspire verification code is: {otp}. This code will expire in 15 minutes."

            # Format phone number to international format for WhatsApp
            # Make sure phone number starts with + and country code
            if not phone_number.startswith("+"):
                phone_number = "+" + phone_number

            # Send message
            message = client.messages.create(
                from_=f"whatsapp:{settings.TWILIO_WHATSAPP_FROM}",
                body=message_body,
                to=f"whatsapp:{phone_number}",
            )

            return message.sid
        except Exception as e:
            # Log error but don't raise exception to prevent registration failure
            print(f"WhatsApp OTP sending failed: {str(e)}")
            return None

    def verify_otp(self, phone_number, otp):
        """
        Verify OTP against the database record.
        """
        try:
            verification = PhoneVerification.objects.filter(
                phone_number=phone_number,
                otp=otp,
                is_verified=False,
                expires_at__gt=timezone.now(),
            ).latest("created_at")

            # Mark as verified
            verification.is_verified = True
            verification.save()

            # Update user verification status
            user = verification.user
            user.is_phone_verified = True
            user.save()

            return True
        except PhoneVerification.DoesNotExist:
            return False

    def get_login_redirect_url(self, request):
        """
        Custom redirect after login based on user role.
        """
        # Redirect to custom login redirect view
        return reverse("accounts:login_redirect")

from django import forms
from django.contrib.auth.forms import UserCreationForm
from allauth.account.forms import SignupForm
from .models import CustomUser, PhoneVerification, StudentProfile, TeacherProfile
from django.utils import timezone

class CustomSignupForm(SignupForm):
    USER_ROLES = (
        ("student", "Student"),
        ("teacher", "Teacher"),
    )
    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"]
        if CustomUser.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("A user with this phone number already exists.")
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        # Ensure clean_phone_number is called
        self.clean_phone_number()
        return cleaned_data

    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    role = forms.ChoiceField(choices=USER_ROLES, required=True)

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.phone_number = self.cleaned_data["phone_number"]
        user.role = self.cleaned_data["role"]
        user.save()

        # Create appropriate profile based on role
        if user.role == "student":
            StudentProfile.objects.create(user=user)
        elif user.role == "teacher":
            TeacherProfile.objects.create(user=user)

        return user


class PhoneVerificationForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Enter 6-digit OTP"}),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(PhoneVerificationForm, self).__init__(*args, **kwargs)

    def clean_otp(self):
        otp = self.cleaned_data["otp"]
        print(otp)

        # Check if OTP exists and is valid
        try:
            verification = PhoneVerification.objects.filter(
                user=self.user,
                otp=otp,
                is_verified=False,
                expires_at__gt=timezone.now(),
            ).latest("created_at")
        except PhoneVerification.DoesNotExist:
            raise forms.ValidationError(
                "Invalid or expired OTP. Please request a new one."
            )

        return otp


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ["grade", "board"]


class TeacherProfileForm(forms.ModelForm):
    class Meta:
        model = TeacherProfile
        fields = ["education", "experience", "bio", "subjects", "profile_picture"]
        widgets = {
            "education": forms.Textarea(attrs={"rows": 3}),
            "experience": forms.Textarea(attrs={"rows": 3}),
            "bio": forms.Textarea(attrs={"rows": 5}),
        }


class TeacherBankDetailsForm(forms.ModelForm):
    class Meta:
        model = TeacherProfile
        fields = ["bank_name", "account_number", "ifsc_code"]

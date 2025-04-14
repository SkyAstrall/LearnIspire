from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .forms import PhoneVerificationForm, StudentProfileForm, TeacherProfileForm
from .adapters import CustomAccountAdapter
from .models import CustomUser

class VerifyPhoneView(LoginRequiredMixin, View):
    template_name = 'account/verify_phone.html'
    
    def get(self, request):
        # Check if already verified
        if request.user.is_phone_verified:
            messages.info(request, "Your phone is already verified.")
            return redirect(self.get_success_url())
        
        form = PhoneVerificationForm(user=request.user)
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = PhoneVerificationForm(request.POST, user=request.user)
        
        if form.is_valid():
            adapter = CustomAccountAdapter()
            otp = form.cleaned_data['otp']
            
            if adapter.verify_otp(request.user.phone_number, otp):
                messages.success(request, "Phone verification successful!")
                return redirect(self.get_success_url())
            else:
                messages.error(request, "Invalid or expired OTP. Please try again.")
        
        return render(request, self.template_name, {'form': form})
    
    def get_success_url(self):
        # Redirect based on user role
        if self.request.user.is_student:
            return reverse('student_dashboard:profile')
        elif self.request.user.is_teacher:
            return reverse('teacher_dashboard:profile')
        else:
            return reverse('landing:home')


class ResendOTPView(LoginRequiredMixin, View):
    def get(self, request):
        # Generate new OTP and send
        adapter = CustomAccountAdapter()
        adapter.generate_otp(request.user, request.user.phone_number)
        
        messages.success(request, "A new OTP has been sent to your WhatsApp account.")
        return redirect('account:verify_phone')


class LoginRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        user_data = CustomUser.objects.get(email=user.email)
        # Redirect based on verificatio status and rol
        if not user_data.is_phone_verified:
            return redirect('account:verify_phone')

        if request.user.is_student:
            return redirect('student_dashboard:home')
        elif request.user.is_teacher:
            return redirect('teacher_dashboard:home')
        elif request.user.is_admin_user:
            return redirect('admin_dashboard:home')
        else:
            return redirect('landing:home')


class StudentProfileUpdateView(LoginRequiredMixin, View):
    template_name = 'account/student_profile_update.html'
    
    def get(self, request):
        if not request.user.is_student:
            messages.error(request, "Access denied.")
            return redirect('landing:home')
        
        try:
            profile = request.user.student_profile
            form = StudentProfileForm(instance=profile)
        except:
            profile = None
            form = StudentProfileForm()
        
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        if not request.user.is_student:
            messages.error(request, "Access denied.")
            return redirect('landing:home')
        
        try:
            profile = request.user.student_profile
            form = StudentProfileForm(request.POST, instance=profile)
        except:
            profile = None
            form = StudentProfileForm(request.POST)
        
        if form.is_valid():
            profile = form.save(commit=False)
            
            if not hasattr(request.user, 'student_profile'):
                profile.user = request.user
            
            profile.save()
            messages.success(request, "Profile updated successfully!")
            
            # Update profile status
            if profile.status == 'NEW':
                profile.update_status('PRICING_REQUESTED')
            
            return redirect('student_dashboard:home')
        
        return render(request, self.template_name, {'form': form})


class TeacherProfileUpdateView(LoginRequiredMixin, View):
    template_name = 'account/teacher_profile_update.html'
    
    def get(self, request):
        if not request.user.is_teacher:
            messages.error(request, "Access denied.")
            return redirect('landing:home')
        
        try:
            profile = request.user.teacher_profile
            form = TeacherProfileForm(instance=profile)
        except:
            profile = None
            form = TeacherProfileForm()
        
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        if not request.user.is_teacher:
            messages.error(request, "Access denied.")
            return redirect('landing:home')
        
        try:
            profile = request.user.teacher_profile
            form = TeacherProfileForm(request.POST, request.FILES, instance=profile)
        except:
            profile = None
            form = TeacherProfileForm(request.POST, request.FILES)
        
        if form.is_valid():
            profile = form.save(commit=False)
            
            if not hasattr(request.user, 'teacher_profile'):
                profile.user = request.user
            
            profile.save()
            form.save_m2m()  # Save many-to-many relationships
            
            messages.success(request, "Profile updated successfully!")
            
            # Update profile status
            if profile.status == 'PENDING':
                messages.info(request, "Your profile has been submitted for review. You'll be notified once approved.")
            
            return redirect('teacher_dashboard:home')
        
        return render(request, self.template_name, {'form': form})

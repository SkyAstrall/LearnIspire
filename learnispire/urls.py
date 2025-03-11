from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # Landing pages
    path("", include("landing.urls")),
    # Authentication
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),
    # Dashboard URLs
    path("student/", include("student_dashboard.urls")),
    path("teacher/", include("teacher_dashboard.urls")),
    path("admin-portal/", include("admin_dashboard.urls")),
    # Feature-based URLs
    path("scheduling/", include("scheduling.urls")),
    path("payments/", include("payments.urls")),
    path("meetings/", include("meetings.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

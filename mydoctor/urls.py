from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.i18n import set_language
from appointments import views as appt_views
from accounts.statistics import statistics_view

# استيراد كافة الدوال المطلوبة من ملف api.py
from appointments.api import (
    api_login, api_register, api_doctors, api_my_appointments,
    api_book_appointment, api_slots,
    api_accept_appointment, api_reject_appointment, api_cancel_appointment,
    api_request_otp, api_verify_otp, api_reset_password, api_change_password
)

admin.site.site_header = "My Doctor"
admin.site.site_title  = "My Doctor"
admin.site.index_title = "Administration"

urlpatterns = [
    path('statistiques/', statistics_view, name='statistics'),
    path('admin/', admin.site.urls),
    path('i18n/setlang/', set_language, name='set_language'),
    path('', appt_views.home, name='home'),
    path('tableau-de-bord/', appt_views.dashboard, name='dashboard'),
    path('', include('accounts.urls')),
    path('', include('appointments.urls')),

    # ── روابط الـ API لتطبيق الهاتف ──────────────────────────
    path('api/login/',    api_login,    name='api_login'),
    path('api/register/', api_register, name='api_register'),
    path('api/doctors/',  api_doctors,  name='api_doctors'),
    path('api/appointments/', api_my_appointments, name='api_appointments'),
    path('api/book/', api_book_appointment, name='api_book'),
    path('api/slots/<int:doctor_id>/', api_slots, name='api_slots'),
    path('api/appointments/<int:appointment_id>/accept/', api_accept_appointment, name='api_accept'),
    path('api/appointments/<int:appointment_id>/reject/', api_reject_appointment, name='api_reject'),
    path('api/appointments/<int:appointment_id>/cancel/', api_cancel_appointment, name='api_cancel'),

    # روابط استعادة كلمة المرور عبر الـ API
    path('api/password/request-otp/', api_request_otp, name='api_request_otp'),
    path('api/password/verify-otp/', api_verify_otp, name='api_verify_otp'),
    path('api/password/reset/', api_reset_password, name='api_reset_password'),
    path('api/password/change/', api_change_password, name='api_change_password'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
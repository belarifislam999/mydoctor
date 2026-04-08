from django.urls import path
from . import views
from .statistics import statistics_view
from accounts.views import (
    password_reset_request,
    password_reset_verify,
    password_reset_confirm,
    change_password,
)
from appointments.api import (
    api_request_otp,
    api_verify_otp,
    api_reset_password,
    api_change_password,
)

urlpatterns = [
    path('connexion/', views.login_view, name='login'),
    path('deconnexion/', views.logout_view, name='logout'),
    path('inscription/', views.register_patient, name='register_patient'),
    path('profil/', views.profile_view, name='profile'),
    path('medecins/', views.doctor_list, name='doctor_list'),
    path('medecins/<int:doctor_id>/', views.doctor_detail, name='doctor_detail'),
    path('admin/statistiques/', statistics_view, name='statistics'),
    path('mot-de-passe-oublie/', password_reset_request, name='password_reset_request'),
    path('verifier-code/', password_reset_verify, name='password_reset_verify'),
    path('nouveau-mot-de-passe/', password_reset_confirm, name='password_reset_confirm'),
    path('changer-mot-de-passe/', change_password, name='change_password'),
    path('api/password/request-otp/',  api_request_otp,    name='api_request_otp'),
    path('api/password/verify-otp/',   api_verify_otp,     name='api_verify_otp'),
    path('api/password/reset/',        api_reset_password,  name='api_reset_password'),
    path('api/password/change/',       api_change_password, name='api_change_password'),
]



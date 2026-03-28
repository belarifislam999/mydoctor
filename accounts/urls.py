from django.urls import path
from . import views

urlpatterns = [
    path('connexion/', views.login_view, name='login'),
    path('deconnexion/', views.logout_view, name='logout'),
    path('inscription/', views.register_patient, name='register_patient'),
    path('profil/', views.profile_view, name='profile'),
    path('medecins/', views.doctor_list, name='doctor_list'),
    path('medecins/<int:doctor_id>/', views.doctor_detail, name='doctor_detail'),
]

from django.urls import path
from . import views
urlpatterns = [
    path('tableau-de-bord/medecin/', views.doctor_dashboard, name='doctor_dashboard'),
    path('tableau-de-bord/patient/', views.patient_dashboard, name='patient_dashboard'),
    path('creneaux/', views.manage_slots, name='manage_slots'),
    path('creneaux/<int:slot_id>/supprimer/', views.delete_slot, name='delete_slot'),
    path('rendez-vous/medecin/', views.doctor_appointments, name='doctor_appointments'),
    path('rendez-vous/medecin/<int:appointment_id>/', views.appointment_detail_doctor, name='appointment_detail_doctor'),
    path('reserver/<int:slot_id>/', views.book_appointment, name='book_appointment'),
    path('rendez-vous/patient/', views.patient_appointments, name='patient_appointments'),
    path('rendez-vous/patient/<int:appointment_id>/', views.appointment_detail_patient, name='appointment_detail_patient'),
]

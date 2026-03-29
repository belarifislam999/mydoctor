"""
accounts/statistics.py
Page d'statistiques des médicaments pour l'Admin
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
import re
from collections import Counter


@staff_member_required
def statistics_view(request):
    from appointments.models import Prescription, Appointment
    from accounts.models import User, DoctorProfile

    today = timezone.now().date()
    month_ago = today - timedelta(days=30)
    year_ago  = today - timedelta(days=365)

    # ── Toutes les ordonnances ──────────────────────────────
    all_prescriptions = Prescription.objects.select_related(
        'appointment__doctor',
        'appointment__doctor__doctor_profile',
        'appointment__patient',
    ).all()

    # ── Compter les médicaments ─────────────────────────────
    all_medications = []
    for presc in all_prescriptions:
        if presc.medications:
            lines = [l.strip() for l in presc.medications.splitlines() if l.strip()]
            for line in lines:
                # Nettoyer la ligne (enlever - et *)
                clean = re.sub(r'^[-*•]\s*', '', line)
                # Prendre seulement le nom (avant le premier chiffre ou tiret)
                name = re.split(r'\s+\d|\s+-\s+|\s+\(', clean)[0].strip()
                if len(name) > 2:
                    all_medications.append(name.title())

    med_counter = Counter(all_medications)
    top_medications = med_counter.most_common(20)

    # ── Compter les diagnostics ─────────────────────────────
    all_diagnoses = []
    for presc in all_prescriptions:
        if presc.diagnosis:
            diag = presc.diagnosis.strip()[:50]
            if diag:
                all_diagnoses.append(diag)

    diag_counter = Counter(all_diagnoses)
    top_diagnoses = diag_counter.most_common(10)

    # ── Statistiques par médecin ────────────────────────────
    doctors_stats = []
    for doctor in User.objects.filter(role='doctor'):
        count = Prescription.objects.filter(
            appointment__doctor=doctor
        ).count()
        patients = Appointment.objects.filter(
            doctor=doctor
        ).values('patient').distinct().count()
        doctors_stats.append({
            'doctor': doctor,
            'prescriptions': count,
            'patients': patients,
        })
    doctors_stats.sort(key=lambda x: x['prescriptions'], reverse=True)

    # ── Statistiques par wilaya ─────────────────────────────
    wilaya_stats = Prescription.objects.filter(
        appointment__doctor__doctor_profile__isnull=False
    ).values(
        'appointment__doctor__doctor_profile__wilaya'
    ).annotate(total=Count('id')).order_by('-total')[:10]

    # ── Statistiques temporelles ────────────────────────────
    today_count   = Prescription.objects.filter(created_at__date=today).count()
    month_count   = Prescription.objects.filter(created_at__date__gte=month_ago).count()
    year_count    = Prescription.objects.filter(created_at__date__gte=year_ago).count()
    total_count   = Prescription.objects.count()

    # ── Patients ayant reçu des ordonnances ────────────────
    patients_with_presc = Prescription.objects.values(
        'appointment__patient'
    ).distinct().count()

    # ── Statistiques générales ──────────────────────────────
    total_doctors   = User.objects.filter(role='doctor').count()
    total_patients  = User.objects.filter(role='patient').count()
    total_appointments = Appointment.objects.count()
    completed_appointments = Appointment.objects.filter(status='termine').count()

    context = {
        'top_medications':    top_medications,
        'top_diagnoses':      top_diagnoses,
        'doctors_stats':      doctors_stats,
        'wilaya_stats':       wilaya_stats,
        'today_count':        today_count,
        'month_count':        month_count,
        'year_count':         year_count,
        'total_count':        total_count,
        'patients_with_presc': patients_with_presc,
        'total_doctors':      total_doctors,
        'total_patients':     total_patients,
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'title': 'Statistiques des Médicaments',
    }
    return render(request, 'admin/statistics.html', context)

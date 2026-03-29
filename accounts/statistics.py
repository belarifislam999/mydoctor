from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from collections import Counter
import re
from accounts.models import WILAYAS


def extract_meds(text):
    if not text:
        return []
    meds = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r'^[-*\u2022\d]+[.)]\s*', '', line).strip()
        if len(line) > 2:
            name = re.split(r'\s+\d|\s*[-]\s*\d|\s+\(', line)[0].strip()
            if len(name) > 2:
                meds.append(name.title())
    return meds


@staff_member_required
def statistics_view(request):
    from appointments.models import Prescription, Appointment
    from accounts.models import User

    today     = timezone.now().date()
    month_ago = today - timedelta(days=30)
    year_ago  = today - timedelta(days=365)

    selected_wilaya = request.GET.get('wilaya', '')
    search_med      = request.GET.get('med', '').strip()
    top_wilaya_mode = request.GET.get('top_wilaya', '') == '1'

    prescriptions_qs = Prescription.objects.select_related(
        'appointment__doctor__doctor_profile',
        'appointment__patient',
    )
    if selected_wilaya:
        prescriptions_qs = prescriptions_qs.filter(
            appointment__doctor__doctor_profile__wilaya=selected_wilaya
        )
    all_prescriptions = list(prescriptions_qs)

    all_meds = []
    for presc in all_prescriptions:
        all_meds.extend(extract_meds(presc.medications))

    med_counter     = Counter(all_meds)
    top_medications = med_counter.most_common(20)
    max_med_count   = top_medications[0][1] if top_medications else 1

    all_diagnoses = []
    for presc in all_prescriptions:
        if presc.diagnosis:
            d = presc.diagnosis.strip()
            if d:
                all_diagnoses.append(d[:60])
    top_diagnoses = Counter(all_diagnoses).most_common(10)

    search_results = []
    search_details = []
    search_total   = 0
    if search_med:
        search_lower = search_med.lower()
        for presc in all_prescriptions:
            for med in extract_meds(presc.medications):
                if search_lower in med.lower():
                    search_results.append(med)
                    try:
                        wilaya_disp = presc.appointment.doctor.doctor_profile.get_wilaya_display()
                    except Exception:
                        wilaya_disp = ''
                    search_details.append({
                        'med':     med,
                        'doctor':  presc.appointment.doctor.get_full_name(),
                        'patient': presc.appointment.patient.get_full_name(),
                        'date':    presc.created_at.date(),
                        'wilaya':  wilaya_disp,
                    })
        search_total = len(search_results)

    wilaya_top_meds = {}
    if top_wilaya_mode:
        all_presc_all = Prescription.objects.select_related('appointment__doctor__doctor_profile')
        wilaya_dict   = {}
        for presc in all_presc_all:
            try:
                w = presc.appointment.doctor.doctor_profile.wilaya
            except Exception:
                continue
            if w:
                meds = extract_meds(presc.medications)
                wilaya_dict.setdefault(w, []).extend(meds)
        wilaya_names = dict(WILAYAS)
        for w, meds in sorted(wilaya_dict.items()):
            if meds:
                wilaya_top_meds[wilaya_names.get(w, w)] = Counter(meds).most_common(3)

    doctors_stats = []
    for doctor in User.objects.filter(role='doctor'):
        qs = Prescription.objects.filter(appointment__doctor=doctor)
        if selected_wilaya:
            qs = qs.filter(appointment__doctor__doctor_profile__wilaya=selected_wilaya)
        count    = qs.count()
        patients = Appointment.objects.filter(doctor=doctor).values('patient').distinct().count()
        doctors_stats.append({'doctor': doctor, 'prescriptions': count, 'patients': patients})
    doctors_stats.sort(key=lambda x: x['prescriptions'], reverse=True)

    base_qs = Prescription.objects
    if selected_wilaya:
        base_qs = base_qs.filter(appointment__doctor__doctor_profile__wilaya=selected_wilaya)

    wilaya_name = dict(WILAYAS).get(selected_wilaya, '') if selected_wilaya else ''

    context = {
        'wilayas':          WILAYAS,
        'selected_wilaya':  selected_wilaya,
        'wilaya_name':      wilaya_name,
        'top_medications':  top_medications,
        'max_med_count':    max_med_count,
        'top_diagnoses':    top_diagnoses,
        'doctors_stats':    doctors_stats,
        'today_count':      base_qs.filter(created_at__date=today).count(),
        'month_count':      base_qs.filter(created_at__date__gte=month_ago).count(),
        'year_count':       base_qs.filter(created_at__date__gte=year_ago).count(),
        'total_count':      base_qs.count(),
        'patients_presc':   Prescription.objects.values('appointment__patient').distinct().count(),
        'total_doctors':    User.objects.filter(role='doctor').count(),
        'total_patients':   User.objects.filter(role='patient').count(),
        'total_appointments': Appointment.objects.count(),
        'completed':        Appointment.objects.filter(status='termine').count(),
        'search_med':       search_med,
        'search_results':   search_results if search_med else None,
        'search_details':   search_details if search_med else None,
        'search_total':     search_total,
        'top_wilaya_mode':  top_wilaya_mode,
        'wilaya_top_meds':  wilaya_top_meds,
        'title':            'Statistiques des Medicaments',
    }
    return render(request, 'admin/statistics.html', context)

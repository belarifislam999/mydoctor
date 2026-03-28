from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta, datetime
from .models import TimeSlot, Appointment, Prescription, Review
from .forms import TimeSlotForm, BulkTimeSlotForm, AppointmentBookingForm, AppointmentNotesForm, PrescriptionForm, ReviewForm
from accounts.models import DoctorProfile, Advertisement


def home(request):
    from accounts.models import User
    from django.conf import settings
    ads_slider  = Advertisement.objects.filter(is_active=True, position='hero').order_by('order')
    ads_top     = Advertisement.objects.filter(is_active=True, position='top')
    ads_bottom  = Advertisement.objects.filter(is_active=True, position='bottom')
    return render(request, 'home.html', {
        'total_doctors':      User.objects.filter(role='doctor').count(),
        'total_patients':     User.objects.filter(role='patient').count(),
        'total_appointments': Appointment.objects.count(),
        'specializations':    DoctorProfile.SPECIALIZATIONS[:8],
        'ads_slider':    ads_slider,
        'ads_top':       ads_top,
        'ads_bottom':    ads_bottom,
        'contact_phone':     getattr(settings, 'CONTACT_PHONE', '0555 000 000'),
        'contact_whatsapp':  getattr(settings, 'CONTACT_WHATSAPP', '213555000000'),
        'contact_email':     getattr(settings, 'CONTACT_EMAIL', 'contact@mydoctor.dz'),
    })


@login_required
def dashboard(request):
    return redirect('doctor_dashboard') if request.user.is_doctor() else redirect('patient_dashboard')


# ─── MÉDECIN ──────────────────────────────────────────────────

@login_required
def doctor_dashboard(request):
    if not request.user.is_doctor():
        return redirect('patient_dashboard')
    today = timezone.now().date()
    user  = request.user
    todays_appts   = Appointment.objects.filter(doctor=user, time_slot__date=today, status='accepte').select_related('patient', 'time_slot')
    pending        = Appointment.objects.filter(doctor=user, status='en_attente').select_related('patient', 'time_slot').order_by('time_slot__date')
    upcoming_count = TimeSlot.objects.filter(doctor=user, is_booked=False, date__gte=today).count()
    completed      = Appointment.objects.filter(doctor=user, status='termine').count()
    total_patients = Appointment.objects.filter(doctor=user).values('patient').distinct().count()
    # Prochain rdv
    next_appt = Appointment.objects.filter(
        doctor=user, status='accepte', time_slot__date__gte=today
    ).select_related('patient', 'time_slot').order_by('time_slot__date', 'time_slot__start_time').first()

    return render(request, 'appointments/doctor_dashboard.html', {
        'todays_appointments': todays_appts,
        'pending_requests':    pending,
        'upcoming_slots':      upcoming_count,
        'total_completed':     completed,
        'total_patients':      total_patients,
        'next_appointment':    next_appt,
        'today': today,
    })


@login_required
def manage_slots(request):
    if not request.user.is_doctor():
        return redirect('patient_dashboard')
    today = timezone.now().date()
    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'single')
        if form_type == 'bulk':
            bulk_form   = BulkTimeSlotForm(request.POST)
            single_form = TimeSlotForm()
            if bulk_form.is_valid():
                date     = bulk_form.cleaned_data['date']
                start    = bulk_form.cleaned_data['start_hour']
                end      = bulk_form.cleaned_data['end_hour']
                duration = int(bulk_form.cleaned_data['slot_duration'])
                current  = datetime.combine(date, start)
                end_dt   = datetime.combine(date, end)
                count = 0
                while current + timedelta(minutes=duration) <= end_dt:
                    slot_end = current + timedelta(minutes=duration)
                    _, created = TimeSlot.objects.get_or_create(
                        doctor=request.user, date=date, start_time=current.time(),
                        defaults={'end_time': slot_end.time()}
                    )
                    if created:
                        count += 1
                    current = slot_end
                messages.success(request, f'{count} créneau(x) créé(s) avec succès !')
                return redirect('manage_slots')
        else:
            single_form = TimeSlotForm(request.POST)
            bulk_form   = BulkTimeSlotForm()
            if single_form.is_valid():
                slot = single_form.save(commit=False)
                slot.doctor = request.user
                if TimeSlot.objects.filter(doctor=request.user, date=slot.date, start_time=slot.start_time).exists():
                    messages.error(request, 'Un créneau existe déjà pour cette date et heure.')
                else:
                    slot.save()
                    messages.success(request, 'Créneau ajouté !')
                    return redirect('manage_slots')
    else:
        single_form = TimeSlotForm()
        bulk_form   = BulkTimeSlotForm()

    upcoming_slots = TimeSlot.objects.filter(doctor=request.user, date__gte=today).order_by('date', 'start_time')
    return render(request, 'appointments/manage_slots.html', {
        'single_form': single_form, 'bulk_form': bulk_form,
        'upcoming_slots': upcoming_slots, 'today': today,
    })


@login_required
def delete_slot(request, slot_id):
    slot = get_object_or_404(TimeSlot, id=slot_id, doctor=request.user)
    if slot.is_booked:
        messages.error(request, 'Impossible de supprimer un créneau réservé.')
    else:
        slot.delete()
        messages.success(request, 'Créneau supprimé.')
    return redirect('manage_slots')


@login_required
def doctor_appointments(request):
    if not request.user.is_doctor():
        return redirect('patient_dashboard')
    appointments = Appointment.objects.filter(doctor=request.user).select_related('patient', 'time_slot').order_by('-time_slot__date')
    status_filter = request.GET.get('status', '')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    return render(request, 'appointments/doctor_appointments.html', {
        'appointments': appointments,
        'status_filter': status_filter,
        'status_choices': Appointment.STATUS_CHOICES,
    })


@login_required
def appointment_detail_doctor(request, appointment_id):
    if not request.user.is_doctor():
        return redirect('patient_dashboard')
    appointment  = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
    prescription = getattr(appointment, 'prescription', None)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_status':
            notes_form = AppointmentNotesForm(request.POST, instance=appointment)
            if notes_form.is_valid():
                updated = notes_form.save(commit=False)
                if updated.status in ['refuse', 'annule']:
                    appointment.time_slot.is_booked = False
                    appointment.time_slot.save()
                updated.save()
                messages.success(request, 'Rendez-vous mis à jour.')
                return redirect('appointment_detail_doctor', appointment_id=appointment_id)
        elif action == 'add_prescription':
            presc_form = PrescriptionForm(request.POST, instance=prescription)
            if presc_form.is_valid():
                presc = presc_form.save(commit=False)
                presc.appointment = appointment
                presc.save()
                appointment.status = 'termine'
                appointment.save()
                messages.success(request, 'Ordonnance enregistrée !')
                return redirect('appointment_detail_doctor', appointment_id=appointment_id)
    notes_form = AppointmentNotesForm(instance=appointment)
    presc_form = PrescriptionForm(instance=prescription)
    return render(request, 'appointments/appointment_detail_doctor.html', {
        'appointment': appointment, 'notes_form': notes_form,
        'presc_form': presc_form, 'prescription': prescription,
    })


# ─── PATIENT ──────────────────────────────────────────────────

@login_required
def patient_dashboard(request):
    user  = request.user
    today = timezone.now().date()
    upcoming = Appointment.objects.filter(
        patient=user, status__in=['en_attente', 'accepte'], time_slot__date__gte=today
    ).select_related('doctor', 'time_slot').order_by('time_slot__date')
    recent = Appointment.objects.filter(
        patient=user, status__in=['termine', 'annule']
    ).select_related('doctor', 'time_slot').order_by('-time_slot__date')[:5]
    return render(request, 'appointments/patient_dashboard.html', {
        'upcoming': upcoming, 'recent': recent, 'today': today,
    })


@login_required
def book_appointment(request, slot_id):
    slot = get_object_or_404(TimeSlot, id=slot_id)
    if not request.user.is_patient():
        messages.error(request, 'Seuls les patients peuvent réserver.')
        return redirect('doctor_list')
    if slot.is_booked:
        messages.error(request, 'Ce créneau est déjà réservé.')
        return redirect('doctor_detail', doctor_id=slot.doctor.doctor_profile.id)
    if slot.is_past():
        messages.error(request, 'Ce créneau est dépassé.')
        return redirect('doctor_detail', doctor_id=slot.doctor.doctor_profile.id)
    if request.method == 'POST':
        form = AppointmentBookingForm(request.POST)
        if form.is_valid():
            appt = form.save(commit=False)
            appt.patient   = request.user
            appt.doctor    = slot.doctor
            appt.time_slot = slot
            appt.status    = Appointment.STATUS_PENDING
            appt.save()
            slot.is_booked = True
            slot.save()
            messages.success(request, f'Rendez-vous réservé avec Dr. {slot.doctor.last_name}. En attente de confirmation.')
            return redirect('patient_dashboard')
    else:
        form = AppointmentBookingForm()
    return render(request, 'appointments/book_appointment.html', {'form': form, 'slot': slot, 'doctor': slot.doctor})


@login_required
def patient_appointments(request):
    appointments = Appointment.objects.filter(patient=request.user).select_related('doctor', 'time_slot').order_by('-time_slot__date')
    status_filter = request.GET.get('status', '')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    return render(request, 'appointments/patient_appointments.html', {
        'appointments': appointments,
        'status_filter': status_filter,
        'status_choices': Appointment.STATUS_CHOICES,
    })


@login_required
def appointment_detail_patient(request, appointment_id):
    appointment     = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    existing_review = getattr(appointment, 'review', None)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'cancel' and appointment.can_be_cancelled():
            appointment.status = Appointment.STATUS_CANCELLED
            appointment.save()
            appointment.time_slot.is_booked = False
            appointment.time_slot.save()
            messages.success(request, 'Rendez-vous annulé.')
            return redirect('patient_appointments')
        elif action == 'review' and not existing_review and appointment.status == 'termine':
            review_form = ReviewForm(request.POST)
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.appointment = appointment
                review.doctor  = appointment.doctor
                review.patient = request.user
                review.save()
                messages.success(request, 'Avis soumis. Merci !')
                return redirect('appointment_detail_patient', appointment_id=appointment_id)
    prescription = getattr(appointment, 'prescription', None)
    review_form  = ReviewForm() if not existing_review else None
    return render(request, 'appointments/appointment_detail_patient.html', {
        'appointment': appointment, 'prescription': prescription,
        'review': existing_review, 'review_form': review_form,
    })

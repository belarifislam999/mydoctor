from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from datetime import timedelta, datetime
from .models import TimeSlot, Appointment, Prescription, Review
from .forms import TimeSlotForm, BulkTimeSlotForm, AppointmentBookingForm, AppointmentNotesForm, PrescriptionForm, ReviewForm
from accounts.models import DoctorProfile, Advertisement


def home(request):
    from accounts.models import User
    from django.conf import settings
    ads_slider = Advertisement.objects.filter(is_active=True, position='hero').order_by('order')
    ads_top    = Advertisement.objects.filter(is_active=True, position='top')
    ads_bottom = Advertisement.objects.filter(is_active=True, position='bottom')
    return render(request, 'home.html', {
        'total_doctors':      User.objects.filter(role='doctor').count(),
        'total_patients':     User.objects.filter(role='patient').count(),
        'total_appointments': Appointment.objects.count(),
        'specializations':    DoctorProfile.SPECIALIZATIONS[:8],
        'ads_slider':         ads_slider,
        'ads_top':            ads_top,
        'ads_bottom':         ads_bottom,
        'contact_phone':      getattr(settings, 'CONTACT_PHONE', '0555 000 000'),
        'contact_whatsapp':   getattr(settings, 'CONTACT_WHATSAPP', '213555000000'),
        'contact_email':      getattr(settings, 'CONTACT_EMAIL', 'contact@mydoctor.dz'),
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
    next_appt      = Appointment.objects.filter(
        doctor=user, status='accepte', time_slot__date__gte=today
    ).select_related('patient', 'time_slot').order_by('time_slot__date', 'time_slot__start_time').first()

    return render(request, 'appointments/doctor_dashboard.html', {
        'todays_appointments': todays_appts,
        'pending_requests':    pending,
        'upcoming_slots':      upcoming_count,
        'total_completed':     completed,
        'total_patients':      total_patients,
        'next_appointment':    next_appt,
        'today':               today,
    })


@login_required
def manage_slots(request):
    if not request.user.is_doctor():
        return redirect('patient_dashboard')

    now_local = timezone.localtime(timezone.now())
    today     = now_local.date()
    now_time  = now_local.time()

    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'single')

        if form_type == 'bulk':
            bulk_form   = BulkTimeSlotForm(request.POST)
            single_form = TimeSlotForm()
            if bulk_form.is_valid():
                date = bulk_form.cleaned_data['date']

                # ── حماية: منع إنشاء في الماضي ───────────
                if date < today:
                    messages.error(request, '❌ Impossible de créer des créneaux dans le passé.')
                    return redirect('manage_slots')

                start    = bulk_form.cleaned_data['start_hour']
                end      = bulk_form.cleaned_data['end_hour']
                duration = int(bulk_form.cleaned_data['slot_duration'])
                current  = datetime.combine(date, start)
                end_dt   = datetime.combine(date, end)
                count    = 0
                while current + timedelta(minutes=duration) <= end_dt:
                    slot_end = current + timedelta(minutes=duration)
                    _, created = TimeSlot.objects.get_or_create(
                        doctor=request.user, date=date,
                        start_time=current.time(),
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

                # ── حماية: منع إنشاء في الماضي ───────────
                if slot.date < today:
                    messages.error(request, '❌ Impossible de créer un créneau dans le passé.')
                    return redirect('manage_slots')

                slot.doctor = request.user
                if TimeSlot.objects.filter(
                    doctor=request.user,
                    date=slot.date,
                    start_time=slot.start_time
                ).exists():
                    messages.error(request, 'Un créneau existe déjà pour cette date et heure.')
                else:
                    slot.save()
                    messages.success(request, 'Créneau ajouté !')
                    return redirect('manage_slots')
    else:
        single_form = TimeSlotForm()
        bulk_form   = BulkTimeSlotForm()

    # ── تنظيف تلقائي: إخفاء الحصص المنتهية ──────────────
    upcoming_slots = TimeSlot.objects.filter(
        doctor=request.user,
        date__gte=today,
    ).exclude(
        date=today,
        start_time__lte=now_time
    ).order_by('date', 'start_time')

    return render(request, 'appointments/manage_slots.html', {
        'single_form':    single_form,
        'bulk_form':      bulk_form,
        'upcoming_slots': upcoming_slots,
        'today':          today,
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

    now_local     = timezone.localtime(timezone.now())
    today         = now_local.date()
    now_time      = now_local.time()
    status_filter = request.GET.get('status', '')
    q             = request.GET.get('q', '').strip()
    date_filter   = request.GET.get('date_filter', '').strip()

    # وضع الأرشيف: عند البحث بالاسم أو التاريخ
    archive_mode = bool(q or date_filter)

    appointments = Appointment.objects.filter(
        doctor=request.user
    ).select_related('patient', 'time_slot').order_by(
        '-time_slot__date', '-time_slot__start_time'
    )

    # ── فلتر الحالة ──────────────────────────────────────
    if status_filter:
        appointments = appointments.filter(status=status_filter)

    # ── التنظيف التلقائي فقط في الوضع العادي ─────────────
    if not archive_mode:
        expired = Q(
            status='en_attente'
        ) & (
            Q(time_slot__date__lt=today) |
            Q(time_slot__date=today, time_slot__start_time__lte=now_time)
        )
        appointments = appointments.exclude(expired)

    # ── بحث بالاسم أو البريد (يفتح الأرشيف) ─────────────
    if q:
        appointments = appointments.filter(
            Q(patient__first_name__icontains=q) |
            Q(patient__last_name__icontains=q)  |
            Q(patient__email__icontains=q)       |
            Q(patient__username__icontains=q)
        )

    # ── فلتر التاريخ (يسمح بالماضي) ──────────────────────
    if date_filter:
        try:
            from datetime import datetime as dt
            filter_date  = dt.strptime(date_filter, '%Y-%m-%d').date()
            appointments = appointments.filter(time_slot__date=filter_date)
        except ValueError:
            pass

    return render(request, 'appointments/doctor_appointments.html', {
        'appointments':   appointments,
        'status_filter':  status_filter,
        'status_choices': Appointment.STATUS_CHOICES,
        'q':              q,
        'date_filter':    date_filter,
        'today':          today,
        'archive_mode':   archive_mode,
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
        'appointment':  appointment,
        'notes_form':   notes_form,
        'presc_form':   presc_form,
        'prescription': prescription,
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
        'upcoming': upcoming,
        'recent':   recent,
        'today':    today,
    })


def doctor_detail(request, doctor_id):
    profile   = get_object_or_404(DoctorProfile, id=doctor_id)
    now_local = timezone.localtime(timezone.now())
    today     = now_local.date()
    now_time  = now_local.time()

    # ── نفس منطق التنظيف التلقائي للطبيب — يُطبَّق على المريض ─
    available_slots = TimeSlot.objects.filter(
        doctor=profile.user,
        is_booked=False,
        date__gte=today,
    ).exclude(
        # إخفاء حصص اليوم التي فات وقتها
        date=today,
        start_time__lte=now_time
    ).order_by('date', 'start_time')

    return render(request, 'accounts/doctor_detail.html', {
        'doctor':          profile,
        'available_slots': available_slots,
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

    # ── منع الحجز المكرر ──────────────────────────────────
    existing = Appointment.objects.filter(
        patient=request.user,
        doctor=slot.doctor,
        time_slot__date=slot.date,
        status__in=['en_attente', 'accepte']
    ).exists()

    if existing:
        messages.error(request, 'Vous avez déjà un rendez-vous avec ce médecin ce jour-là.')
        return redirect('doctor_detail', doctor_id=slot.doctor.doctor_profile.id)

    if request.method == 'POST':
        form = AppointmentBookingForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    slot_locked = TimeSlot.objects.select_for_update().get(id=slot_id)

                    if slot_locked.is_booked or Appointment.objects.filter(time_slot=slot_locked).exists():
                        messages.error(request, 'Désolé, ce créneau vient d\'être réservé. Choisissez un autre.')
                        return redirect('doctor_detail', doctor_id=slot.doctor.doctor_profile.id)

                    appt = form.save(commit=False)
                    appt.patient   = request.user
                    appt.doctor    = slot_locked.doctor
                    appt.time_slot = slot_locked
                    appt.status    = 'en_attente'
                    appt.save()

                    slot_locked.is_booked = True
                    slot_locked.save()

                messages.success(request, f'Rendez-vous réservé avec Dr. {slot.doctor.last_name}. En attente de confirmation.')
                return redirect('patient_dashboard')

            except Exception:
                messages.error(request, 'Une erreur est survenue. Veuillez réessayer.')
                return redirect('doctor_detail', doctor_id=slot.doctor.doctor_profile.id)
    else:
        form = AppointmentBookingForm()

    return render(request, 'appointments/book_appointment.html', {
        'form': form, 'slot': slot, 'doctor': slot.doctor
    })


@login_required
def patient_appointments(request):
    appointments  = Appointment.objects.filter(patient=request.user).select_related('doctor', 'time_slot').order_by('-time_slot__date')
    status_filter = request.GET.get('status', '')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    return render(request, 'appointments/patient_appointments.html', {
        'appointments':   appointments,
        'status_filter':  status_filter,
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
                review.doctor      = appointment.doctor
                review.patient     = request.user
                review.save()
                messages.success(request, 'Avis soumis. Merci !')
                return redirect('appointment_detail_patient', appointment_id=appointment_id)
    prescription = getattr(appointment, 'prescription', None)
    review_form  = ReviewForm() if not existing_review else None
    return render(request, 'appointments/appointment_detail_patient.html', {
        'appointment':  appointment,
        'prescription': prescription,
        'review':       existing_review,
        'review_form':  review_form,
    })


# ─── قبول / رفض / إلغاء ───────────────────────────────────────

@login_required
def accept_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
    appointment.status = 'accepte'
    appointment.save()
    Appointment.objects.filter(time_slot=appointment.time_slot).exclude(id=appointment.id).update(status='refuse')
    messages.success(request, 'Rendez-vous accepté.')
    return redirect('doctor_dashboard')


@login_required
def refuse_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
    appointment.status = 'refuse'
    appointment.save()
    slot = appointment.time_slot
    slot.is_booked = False
    slot.save()
    messages.info(request, 'Rendez-vous refusé et créneau libéré.')
    return redirect('doctor_dashboard')


@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    appointment.status = 'annule'
    appointment.save()
    slot = appointment.time_slot
    slot.is_booked = False
    slot.save()
    messages.success(request, 'Rendez-vous annulé.')
    return redirect('patient_dashboard')

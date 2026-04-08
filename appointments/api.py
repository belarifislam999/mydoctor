from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from accounts.models import User, DoctorProfile
from .models import Appointment, TimeSlot
from django.utils import timezone
from django.db.models import Q
from django.conf import settings  # هذا السطر كان ناقصاً ويسبب توقف الملف



# ── تسجيل حساب جديد (مريض) ────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    username   = request.data.get('username', '').strip()
    email      = request.data.get('email', '').strip()
    password   = request.data.get('password', '')
    full_name  = request.data.get('full_name', '').strip()
    first_name = request.data.get('first_name', '').strip()
    last_name  = request.data.get('last_name', '').strip()

    if full_name and not first_name:
        parts      = full_name.split(' ', 1)
        first_name = parts[0]
        last_name  = parts[1] if len(parts) > 1 else ''

    if not username or not email or not password:
        return Response({'error': 'username, email et password sont obligatoires'}, status=400)
    if User.objects.filter(username=username).exists():
        return Response({'error': "Ce nom d'utilisateur est déjà pris"}, status=400)
    if User.objects.filter(email=email).exists():
        return Response({'error': 'Cet email est déjà utilisé'}, status=400)
    if len(password) < 6:
        return Response({'error': 'Le mot de passe doit contenir au moins 6 caractères'}, status=400)
    try:
        user = User.objects.create_user(
            username=username, email=email, password=password,
            first_name=first_name, last_name=last_name, role='patient',
        )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'message': 'Compte créé avec succès', 'token': token.key,
            'user_id': user.id, 'username': user.username,
            'role': user.role, 'full_name': user.get_full_name(),
        }, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


# ── تسجيل الدخول ──────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    identifier = request.data.get('username', '').strip()
    password   = request.data.get('password', '')
    user = authenticate(username=identifier, password=password)
    if not user:
        try:
            u = User.objects.get(Q(email=identifier) | Q(phone_number=identifier))
            user = authenticate(username=u.username, password=password)
        except User.DoesNotExist:
            user = None
    if not user:
        return Response({'error': 'Identifiants incorrects'}, status=400)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        'token': token.key, 'user_id': user.id,
        'username': user.username, 'role': user.role,
        'full_name': user.get_full_name(),
    })


# ── خريطة التخصصات ────────────────────────────────────────
SPEC_MAP = {
    'gastro-entérologie': 'gastro', 'gastroenterologie': 'gastro',
    'gastro': 'gastro', 'gastroentérologue': 'gastro',
    'endocrinologie': 'endocrino', 'endocrino': 'endocrino',
    'diabétologie': 'endocrino', 'diabetologie': 'endocrino',
    'endocrinologie - diabétologie': 'endocrino',
    'rhumatologie': 'rhumato', 'rhumato': 'rhumato',
    'rhumatologue': 'rhumato',
    'pneumologie': 'pneumo', 'pneumo': 'pneumo',
    'pneumologue': 'pneumo',
    'néphrologie': 'nephro', 'nephrologie': 'nephro',
    'nephro': 'nephro', 'néphrologue': 'nephro',
    'chirurgie générale': 'chir_gen', 'chirurgie generale': 'chir_gen',
    'chir_gen': 'chir_gen', 'chirurgien': 'chir_gen',
    'médecine interne': 'med_interne', 'medecine interne': 'med_interne',
    'med_interne': 'med_interne', 'interniste': 'med_interne',
    'nutrition': 'nutrition', 'nutritionniste': 'nutrition',
    'diététique': 'nutrition',
    'psychologie': 'psychologie', 'psychologue': 'psychologie',
    'kinésithérapie': 'kine', 'kinesitherapie': 'kine',
    'kine': 'kine', 'kinésithérapeute': 'kine',
    'rééducation': 'kine', 'reeducation': 'kine',
}


# ── قائمة الأطباء مع فلترة ────────────────────────────────
@api_view(['GET'])
@permission_classes([AllowAny])
def api_doctors(request):
    wilaya = request.query_params.get('wilaya', '').strip()
    spec   = request.query_params.get('specialization', '').strip()
    qs = User.objects.filter(role='doctor').select_related('doctor_profile')
    if wilaya:
        qs = qs.filter(doctor_profile__wilaya=wilaya)
    if spec:
        spec_lower = spec.lower().strip()
        spec_code  = SPEC_MAP.get(spec_lower, spec_lower)
        qs = qs.filter(
            Q(doctor_profile__specialization__iexact=spec_code) |
            Q(doctor_profile__specialization__icontains=spec_lower) |
            Q(doctor_profile__specialization__icontains=spec_code)
        )
    data = []
    for doc in qs:
        try:
            p = doc.doctor_profile
            data.append({
                'id': doc.id, 'full_name': doc.get_full_name() or doc.username,
                'specialization': p.get_specialization_display(),
                'wilaya': p.get_wilaya_display(), 'wilaya_code': p.wilaya,
                'commune': p.commune or '', 'bio': p.bio or '',
                'fee': float(p.consultation_fee or 0),
                'consultation_fee': float(p.consultation_fee or 0),
                'years_experience': int(p.years_of_experience or 0),
                'years_of_experience': int(p.years_of_experience or 0),
                'clinic_address': p.clinic_address or '',
                'location_url': p.location_url or p.clinic_address or '',
                'phone_number': doc.phone_number or '',
                'is_available': p.is_available,
                'phone': doc.phone_number or '',
                'photo': request.build_absolute_uri(doc.profile_picture.url)
                         if doc.profile_picture else None,
            })
        except Exception:
            continue
    return Response(data)


# ── المواعيد المتاحة لطبيب معين (مع فلترة الوقت الماضي) ───
@api_view(['GET'])
@permission_classes([AllowAny])
def api_slots(request, doctor_id):
    now_local = timezone.localtime(timezone.now())
    today     = now_local.date()

    slots = TimeSlot.objects.filter(
        doctor_id=doctor_id,
        is_booked=False,
        date__gte=today,
    ).exclude(
        date=today,
        start_time__lte=now_local.time()
    ).order_by('date', 'start_time')

    data = []
    for s in slots:
        start = s.start_time.strftime('%H:%M') if s.start_time else ''
        end   = s.end_time.strftime('%H:%M')   if s.end_time   else ''
        data.append({
            'id': s.id, 'date': str(s.date),
            'time': start, 'start_time': start, 'end_time': end,
            'display': f'{start} - {end}', 'is_booked': s.is_booked,
        })
    return Response(data)


# ── مواعيد المريض الحالي ───────────────────────────────────
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_my_appointments(request):
    appointments = Appointment.objects.filter(
        patient=request.user,
        time_slot__date__gte=timezone.now().date()
    ).select_related('doctor__doctor_profile', 'time_slot').order_by(
        'time_slot__date', 'time_slot__start_time')
    data = []
    for apt in appointments:
        try:
            spec = apt.doctor.doctor_profile.get_specialization_display()
        except Exception:
            spec = ''
        if apt.time_slot:
            apt_date  = str(apt.time_slot.date)
            apt_start = apt.time_slot.start_time.strftime('%H:%M') if apt.time_slot.start_time else ''
            apt_end   = apt.time_slot.end_time.strftime('%H:%M')   if apt.time_slot.end_time   else ''
            apt_time  = f'{apt_start} - {apt_end}' if apt_end else apt_start
        else:
            apt_date = apt_start = apt_end = apt_time = ''
        data.append({
            'id': apt.id,
            'doctor': apt.doctor.get_full_name() or apt.doctor.username,
            'doctor_name': apt.doctor.get_full_name() or apt.doctor.username,
            'patient_name': apt.patient.get_full_name() or apt.patient.username,
            'specialization': spec, 'date': apt_date, 'time': apt_time,
            'start_time': apt_start, 'end_time': apt_end,
            'status': apt.status, 'reason': apt.reason or '',
        })
    return Response(data)


# ── مواعيد الطبيب ─────────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_doctor_appointments(request):
    appointments = Appointment.objects.filter(
        doctor=request.user,
        time_slot__date__gte=timezone.now().date()
    ).select_related('patient', 'time_slot').order_by(
        'time_slot__date', 'time_slot__start_time')
    data = []
    for apt in appointments:
        if apt.time_slot:
            apt_date  = str(apt.time_slot.date)
            apt_start = apt.time_slot.start_time.strftime('%H:%M') if apt.time_slot.start_time else ''
            apt_end   = apt.time_slot.end_time.strftime('%H:%M')   if apt.time_slot.end_time   else ''
            apt_time  = f'{apt_start} - {apt_end}' if apt_end else apt_start
        else:
            apt_date = apt_start = apt_end = apt_time = ''
        data.append({
            'id': apt.id,
            'doctor_name': apt.doctor.get_full_name() or apt.doctor.username,
            'patient_name': apt.patient.get_full_name() or apt.patient.username,
            'date': apt_date, 'time': apt_time,
            'start_time': apt_start, 'end_time': apt_end,
            'status': apt.status, 'reason': apt.reason or '',
        })
    return Response(data)


# ── حجز موعد ──────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_book_appointment(request):
    doctor_id = request.data.get('doctor_id')
    slot_id   = request.data.get('slot_id')
    reason    = request.data.get('reason', '')
    try:
        with transaction.atomic():
            doctor = User.objects.get(id=doctor_id, role='doctor')
            slot   = TimeSlot.objects.select_for_update().get(id=slot_id, is_booked=False)

            # منع الحجز المكرر
            already = Appointment.objects.filter(
                patient=request.user, doctor=doctor,
                time_slot__date=slot.date,
            ).exclude(status__in=['refuse', 'annule']).exists()
            if already:
                return Response(
                    {'error': "Vous avez déjà un rendez-vous avec ce médecin ce jour-là. Attendez qu'il soit refusé ou annulé pour réessayer."},
                    status=400
                )
            apt = Appointment.objects.create(
                patient=request.user, doctor=doctor,
                time_slot=slot, reason=reason, status='en_attente',
            )
            slot.is_booked = True
            slot.save()
            return Response({'success': True, 'appointment_id': apt.id})
    except TimeSlot.DoesNotExist:
        return Response({'error': "Ce créneau n'est plus disponible."}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


# ── قبول موعد + رفض تلقائي للمتصادمين ────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_accept_appointment(request, appointment_id):
    try:
        with transaction.atomic():
            apt = Appointment.objects.get(id=appointment_id)
            apt.status = 'accepte'
            apt.save()
            if apt.time_slot:
                conflicts = Appointment.objects.filter(
                    time_slot=apt.time_slot, status='en_attente'
                ).exclude(id=apt.id)
                for c in conflicts:
                    c.status = 'refuse'
                    c.save()
            return Response({
                'success': True, 'status': 'accepte',
                'message': 'Rendez-vous accepté. Les autres demandes ont été refusées automatiquement.',
            })
    except Appointment.DoesNotExist:
        return Response({'error': 'Rendez-vous introuvable'}, status=404)


# ── رفض موعد + تحرير الخانة ───────────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_reject_appointment(request, appointment_id):
    try:
        apt = Appointment.objects.get(id=appointment_id)
        apt.status = 'refuse'
        if apt.time_slot:
            apt.time_slot.is_booked = False
            apt.time_slot.save()
        apt.save()
        return Response({
            'success': True, 'status': 'refuse',
            'message': 'Rendez-vous refusé. Le créneau est maintenant disponible.',
        })
    except Appointment.DoesNotExist:
        return Response({'error': 'Rendez-vous introuvable'}, status=404)


# ── إلغاء موعد (من المريض) ────────────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_cancel_appointment(request, appointment_id):
    try:
        apt = Appointment.objects.get(id=appointment_id, patient=request.user)
        if apt.status in ['accepte', 'en_attente']:
            apt.status = 'annule'
            if apt.time_slot:
                apt.time_slot.is_booked = False
                apt.time_slot.save()
            apt.save()
            return Response({
                'success': True, 'status': 'annule',
                'message': 'Rendez-vous annulé. Le créneau a été libéré.',
            })
        return Response({
            'error': 'Ce rendez-vous ne peut pas être annulé.',
            'current_status': apt.status,
        }, status=400)
    except Appointment.DoesNotExist:
        return Response({'error': 'Rendez-vous introuvable'}, status=404)



# ── API: Demande OTP ──────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def api_request_otp(request):
    email = request.data.get('email', '').strip()
    if not email:
        return Response({'error': 'Email requis'}, status=400)
    try:
        from accounts.models import User, PasswordResetOTP
        from django.core.mail import send_mail
        user = User.objects.get(email=email)
        otp  = PasswordResetOTP.generate_for(user)

        send_mail(
            subject='My Doctor — Code de réinitialisation',
            message=f'Votre code est : {otp.code}\nValable 10 minutes.\n\nرمزك هو: {otp.code}\nصالح لمدة 10 دقائق.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return Response({'message': f'Code envoyé à {email}'})
    except User.DoesNotExist:
        # سبب أمني: لا نكشف إن كان الإيميل موجوداً
        return Response({'message': f'Si un compte existe pour {email}, un code a été envoyé.'})
    except Exception as e:
        return Response({'error': f'Erreur envoi email: {str(e)}'}, status=500)


# ── API: Vérification OTP ─────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def api_verify_otp(request):
    email = request.data.get('email', '').strip()
    code  = request.data.get('code', '').strip()
    if not email or not code:
        return Response({'error': 'Email et code requis'}, status=400)
    try:
        from accounts.models import User, PasswordResetOTP
        user = User.objects.get(email=email)
        otp  = PasswordResetOTP.objects.filter(user=user, code=code).last()
        if otp and otp.is_valid():
            # Ne pas marquer comme utilisé ici — on attend le reset
            return Response({'valid': True, 'message': 'Code valide'})
        return Response({'valid': False, 'error': 'Code invalide ou expiré'}, status=400)
    except User.DoesNotExist:
        return Response({'error': 'Compte introuvable'}, status=404)


# ── API: Réinitialisation du mot de passe ─────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def api_reset_password(request):
    email     = request.data.get('email', '').strip()
    code      = request.data.get('code', '').strip()
    password  = request.data.get('password', '')
    if not all([email, code, password]):
        return Response({'error': 'email, code et password requis'}, status=400)
    if len(password) < 6:
        return Response({'error': 'Le mot de passe doit contenir au moins 6 caractères'}, status=400)
    try:
        from accounts.models import User, PasswordResetOTP
        user = User.objects.get(email=email)
        otp  = PasswordResetOTP.objects.filter(user=user, code=code).last()
        if not otp or not otp.is_valid():
            return Response({'error': 'Code invalide ou expiré'}, status=400)
        user.set_password(password)
        user.save()
        otp.is_used = True
        otp.save()
        # Générer nouveau token
        from rest_framework.authtoken.models import Token
        Token.objects.filter(user=user).delete()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'success': True,
            'message': 'Mot de passe réinitialisé avec succès',
            'token': token.key,
        })
    except User.DoesNotExist:
        return Response({'error': 'Compte introuvable'}, status=404)


# ── API: Changement mot de passe (connecté) ───────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_change_password(request):
    current  = request.data.get('current_password', '')
    new_pass = request.data.get('new_password', '')
    if not request.user.check_password(current):
        return Response({'error': 'Mot de passe actuel incorrect'}, status=400)
    if len(new_pass) < 6:
        return Response({'error': 'Au moins 6 caractères requis'}, status=400)
    request.user.set_password(new_pass)
    request.user.save()
    from rest_framework.authtoken.models import Token
    Token.objects.filter(user=request.user).delete()
    token, _ = Token.objects.get_or_create(user=request.user)
    return Response({
        'success': True,
        'message': 'Mot de passe modifié',
        'token': token.key,
    })

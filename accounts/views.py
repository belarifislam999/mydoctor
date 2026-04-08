from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import User, DoctorProfile, PatientProfile, Advertisement, WILAYAS
from .forms import PatientRegistrationForm, CustomLoginForm, UserUpdateForm, DoctorProfileForm, PatientProfileForm
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import update_session_auth_hash

def register_patient(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Bienvenue, {user.first_name} ! Votre compte a été créé.')
            return redirect('dashboard')
    else:
        form = PatientRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            identifiant = form.cleaned_data['identifiant']
            password    = form.cleaned_data['password']
            user = None

            # 1) Chercher par nom d'utilisateur
            try:
                u = User.objects.get(username=identifiant)
                from django.contrib.auth import authenticate
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                pass

            # 2) Chercher par email
            if user is None:
                try:
                    u = User.objects.get(email__iexact=identifiant)
                    from django.contrib.auth import authenticate
                    user = authenticate(request, username=u.username, password=password)
                except User.DoesNotExist:
                    pass

            # 3) Chercher par numéro de téléphone
            if user is None:
                try:
                    u = User.objects.get(phone_number=identifiant)
                    from django.contrib.auth import authenticate
                    user = authenticate(request, username=u.username, password=password)
                except User.DoesNotExist:
                    pass

            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f'Bienvenue, {user.first_name or user.username} !')
                    return redirect(request.GET.get('next', 'dashboard'))
                else:
                    messages.error(request, 'Ce compte est désactivé.')
            else:
                messages.error(request, 'Identifiant ou mot de passe incorrect.')
    else:
        form = CustomLoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Vous avez été déconnecté.')
    return redirect('home')


@login_required
def profile_view(request):
    user = request.user
    if user.is_doctor():
        profile, _ = DoctorProfile.objects.get_or_create(user=user)
        ProfileForm = DoctorProfileForm
        template = 'accounts/doctor_profile.html'
    else:
        profile, _ = PatientProfile.objects.get_or_create(user=user)
        ProfileForm = PatientProfileForm
        template = 'accounts/patient_profile.html'

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, request.FILES, instance=user)
        profile_form = ProfileForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profil mis à jour avec succès !')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileForm(instance=profile)

    return render(request, template, {'user_form': user_form, 'profile_form': profile_form, 'profile': profile})



def doctor_list(request):
    """Liste des médecins avec recherche par wilaya, commune et spécialisation."""
    doctors = DoctorProfile.objects.filter(is_available=True).select_related('user')

    search_query = request.GET.get('search', '')
    spec_filter = request.GET.get('specialization', '')
    wilaya_filter = request.GET.get('wilaya', '')
    commune_filter = request.GET.get('commune', '')

    if search_query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(commune__icontains=search_query)
        )
    if spec_filter:
        doctors = doctors.filter(specialization=spec_filter)
    if wilaya_filter:
        doctors = doctors.filter(wilaya=wilaya_filter)
    if commune_filter:
        doctors = doctors.filter(commune__icontains=commune_filter)

    # Publicités sidebar
    ads_sidebar = Advertisement.objects.filter(is_active=True, position='sidebar')

    return render(request, 'accounts/doctor_list.html', {
        'doctors': doctors,
        'specializations': DoctorProfile.SPECIALIZATIONS,
        'wilayas': WILAYAS,
        'search_query': search_query,
        'spec_filter': spec_filter,
        'wilaya_filter': wilaya_filter,
        'commune_filter': commune_filter,
        'ads_sidebar': ads_sidebar,
    })


def doctor_detail(request, doctor_id):
    doctor_profile = get_object_or_404(DoctorProfile, id=doctor_id)
    from appointments.models import TimeSlot
    from django.utils import timezone
    available_slots = TimeSlot.objects.filter(
        doctor=doctor_profile.user, is_booked=False, date__gte=timezone.now().date()
    ).order_by('date', 'start_time')
    return render(request, 'accounts/doctor_detail.html', {
        'doctor': doctor_profile,
        'available_slots': available_slots,
    })
# ── Password Reset OTP ─────────────────────────────────────
from django.core.mail import send_mail
from django.contrib.auth import update_session_auth_hash

def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        try:
            from accounts.models import PasswordResetOTP
            user = User.objects.get(email=email)
            otp  = PasswordResetOTP.generate_for(user)
            send_mail(
                subject='My Doctor — Code de réinitialisation',
                message=f'Votre code : {otp.code}\nValable 10 minutes.\n\nرمزك: {otp.code}\nصالح 10 دقائق.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            request.session['reset_email'] = email
            messages.success(request, f'Code envoyé à {email}')
            return redirect('password_reset_verify')
        except User.DoesNotExist:
            messages.error(request, 'Aucun compte trouvé avec cet email.')
    return render(request, 'accounts/password_reset_request.html')


def password_reset_verify(request):
    email = request.session.get('reset_email', '')
    if not email:
        return redirect('password_reset_request')
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        try:
            from accounts.models import PasswordResetOTP
            user = User.objects.get(email=email)
            otp  = PasswordResetOTP.objects.filter(user=user, code=code).last()
            if otp and otp.is_valid():
                otp.is_used = True
                otp.save()
                request.session['reset_user_id'] = user.id
                return redirect('password_reset_confirm')
            else:
                messages.error(request, 'Code invalide ou expiré.')
        except User.DoesNotExist:
            return redirect('password_reset_request')
    return render(request, 'accounts/password_reset_verify.html', {'email': email})


def password_reset_confirm(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('password_reset_request')
    if request.method == 'POST':
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        if len(password1) < 6:
            messages.error(request, 'Minimum 6 caractères.')
        elif password1 != password2:
            messages.error(request, 'Les mots de passe ne correspondent pas.')
        else:
            user = User.objects.get(id=user_id)
            user.set_password(password1)
            user.save()
            del request.session['reset_user_id']
            del request.session['reset_email']
            messages.success(request, '✅ Mot de passe modifié. Connectez-vous.')
            return redirect('login')
    return render(request, 'accounts/password_reset_confirm.html')


@login_required
def change_password(request):
    if request.method == 'POST':
        current  = request.POST.get('current_password', '')
        new_pass = request.POST.get('new_password', '')
        confirm  = request.POST.get('confirm_password', '')
        if not request.user.check_password(current):
            messages.error(request, 'Mot de passe actuel incorrect.')
        elif len(new_pass) < 6:
            messages.error(request, 'Minimum 6 caractères.')
        elif new_pass != confirm:
            messages.error(request, 'Les mots de passe ne correspondent pas.')
        else:
            request.user.set_password(new_pass)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, '✅ Mot de passe changé.')
            return redirect('profile')
    return render(request, 'accounts/change_password.html')
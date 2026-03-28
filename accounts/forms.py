from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User, DoctorProfile, PatientProfile, WILAYAS


class PatientRegistrationForm(UserCreationForm):
    first_name   = forms.CharField(max_length=50, required=True, label="Prénom / الاسم")
    last_name    = forms.CharField(max_length=50, required=True, label="Nom / اللقب")
    email        = forms.EmailField(required=True, label="Email")
    phone_number = forms.CharField(max_length=20, required=False, label="Téléphone / الهاتف")

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label      = "Nom d'utilisateur"
        self.fields['username'].help_text  = "Lettres, chiffres et @/./+/-/_ uniquement."
        self.fields['password1'].label     = "Mot de passe (min. 6 caractères)"
        self.fields['password1'].help_text = ""
        self.fields['password2'].label     = "Confirmer le mot de passe"
        self.fields['password2'].help_text = ""

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("❌ Cet email est déjà utilisé par un autre compte.")
        return email.lower()

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            if User.objects.filter(phone_number=phone).exists():
                raise ValidationError("❌ Ce numéro de téléphone est déjà utilisé par un autre compte.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role         = User.ROLE_PATIENT
        user.email        = self.cleaned_data['email']
        user.phone_number = self.cleaned_data.get('phone_number') or None
        if commit:
            user.save()
            PatientProfile.objects.create(user=user)
        return user


class CustomLoginForm(forms.Form):
    identifiant = forms.CharField(
        label="Identifiant",
        widget=forms.TextInput(attrs={
            'placeholder': "Nom d'utilisateur, email ou téléphone",
            'autofocus': True
        })
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'placeholder': 'Mot de passe'})
    )


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'profile_picture']
        labels = {
            'first_name':     'Prénom',
            'last_name':      'Nom',
            'email':          'Email',
            'phone_number':   'Téléphone',
            'profile_picture':'Photo de profil',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("❌ Cet email est déjà utilisé.")
        return email.lower()

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            qs = User.objects.filter(phone_number=phone).exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("❌ Ce numéro est déjà utilisé.")
        return phone or None


class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model  = DoctorProfile
        fields = ['specialization','wilaya','commune','bio','years_of_experience','consultation_fee','clinic_address','is_available']
        widgets = {
            'bio':           forms.Textarea(attrs={'rows': 4}),
            'clinic_address':forms.Textarea(attrs={'rows': 2}),
        }


class PatientProfileForm(forms.ModelForm):
    class Meta:
        model  = PatientProfile
        fields = ['wilaya','date_of_birth','blood_group','allergies','medical_history','emergency_contact_name','emergency_contact_phone']
        widgets = {
            'date_of_birth':  forms.DateInput(attrs={'type': 'date'}),
            'allergies':      forms.Textarea(attrs={'rows': 3}),
            'medical_history':forms.Textarea(attrs={'rows': 3}),
        }

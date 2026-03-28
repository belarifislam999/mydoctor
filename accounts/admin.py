from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, DoctorProfile, PatientProfile, Advertisement, WILAYAS


class DoctorProfileInline(admin.StackedInline):
    model = DoctorProfile
    can_delete = False
    verbose_name_plural = 'Profil Médecin'
    fields = ['specialization', 'wilaya', 'commune', 'bio', 'years_of_experience', 'consultation_fee', 'clinic_address', 'is_available']


class PatientProfileInline(admin.StackedInline):
    model = PatientProfile
    can_delete = False
    verbose_name_plural = 'Profil Patient'
    fields = ['wilaya', 'date_of_birth', 'blood_group', 'allergies', 'medical_history', 'emergency_contact_name', 'emergency_contact_phone']


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'email', 'role_badge', 'phone_number', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    fieldsets = UserAdmin.fieldsets + (
        ('Rôle & Contact', {'fields': ('role', 'phone_number', 'profile_picture')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'email', 'role', 'phone_number', 'password1', 'password2'),
        }),
    )

    def role_badge(self, obj):
        if obj.role == 'doctor':
            return format_html('<span style="background:#dcfce7;color:#14532d;padding:3px 10px;border-radius:10px;font-size:12px;font-weight:600">🩺 Médecin</span>')
        return format_html('<span style="background:#dbeafe;color:#1e40af;padding:3px 10px;border-radius:10px;font-size:12px;font-weight:600">👤 Patient</span>')
    role_badge.short_description = 'Rôle'

    def get_inlines(self, request, obj=None):
        if obj:
            if obj.role == User.ROLE_DOCTOR:
                return [DoctorProfileInline]
            elif obj.role == User.ROLE_PATIENT:
                return [PatientProfileInline]
        return []

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.role == User.ROLE_DOCTOR:
            DoctorProfile.objects.get_or_create(user=obj)
        elif obj.role == User.ROLE_PATIENT:
            PatientProfile.objects.get_or_create(user=obj)


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'specialization', 'wilaya_display', 'commune', 'consultation_fee', 'is_available']
    list_filter = ['specialization', 'wilaya', 'is_available']
    search_fields = ['user__first_name', 'user__last_name', 'commune']

    def wilaya_display(self, obj):
        return obj.get_wilaya_display()
    wilaya_display.short_description = 'Wilaya'


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'wilaya', 'blood_group', 'date_of_birth']
    search_fields = ['user__first_name', 'user__last_name']


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ['title', 'position_badge', 'is_active', 'order', 'preview_colors', 'created_at']
    list_filter = ['is_active', 'position']
    list_editable = ['is_active', 'order']
    search_fields = ['title', 'description']

    fieldsets = (
        ('Contenu', {
            'fields': ('title', 'description', 'image', 'link_url', 'link_text')
        }),
        ('Affichage', {
            'fields': ('position', 'background_color', 'text_color', 'order', 'is_active')
        }),
    )

    def position_badge(self, obj):
        colors = {
            'hero': '#7c3aed', 'top': '#0066ff',
            'sidebar': '#0891b2', 'bottom': '#64748b'
        }
        color = colors.get(obj.position, '#64748b')
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:8px;font-size:11px">{}</span>',
            color, obj.get_position_display()
        )
    position_badge.short_description = 'Position'

    def preview_colors(self, obj):
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:6px;font-size:12px">Aperçu</span>',
            obj.background_color, obj.text_color
        )
    preview_colors.short_description = 'Aperçu couleurs'

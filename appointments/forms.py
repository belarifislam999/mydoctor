from django import forms
from django.utils import timezone
from datetime import datetime, timedelta
from .models import TimeSlot, Appointment, Prescription, Review


class TimeSlotForm(forms.ModelForm):
    class Meta:
        model = TimeSlot
        fields = ['date', 'start_time', 'end_time']
        labels = {'date': 'Date', 'start_time': 'Heure de début', 'end_time': 'Heure de fin'}
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        start = cleaned_data.get('start_time')
        end   = cleaned_data.get('end_time')
        if date and date < timezone.now().date():
            raise forms.ValidationError("Impossible de créer un créneau dans le passé.")
        if start and end and end <= start:
            raise forms.ValidationError("L'heure de fin doit être après l'heure de début.")
        return cleaned_data


class BulkTimeSlotForm(forms.Form):
    date       = forms.DateField(label="Date", widget=forms.DateInput(attrs={'type': 'date'}))
    start_hour = forms.TimeField(label="Début", widget=forms.TimeInput(attrs={'type': 'time'}))
    end_hour   = forms.TimeField(label="Fin",   widget=forms.TimeInput(attrs={'type': 'time'}))
    slot_duration = forms.ChoiceField(label="Durée", choices=[
        (15,'15 min'), (20,'20 min'), (30,'30 min'), (45,'45 min'), (60,'1 heure')
    ])


class AppointmentBookingForm(forms.ModelForm):
    class Meta:
        model  = Appointment
        fields = ['reason']
        labels = {'reason': 'Motif de consultation'}
        widgets = {'reason': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Décrivez vos symptômes...'})}


class AppointmentNotesForm(forms.ModelForm):
    class Meta:
        model  = Appointment
        fields = ['doctor_notes', 'status']
        labels = {'doctor_notes': 'Notes', 'status': 'Statut'}
        widgets = {'doctor_notes': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].choices = [
            ('accepte', 'Accepté'), ('refuse', 'Refusé'),
            ('termine', 'Terminé'), ('annule', 'Annulé'),
        ]


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model  = Prescription
        fields = ['diagnosis', 'medications', 'instructions', 'follow_up_date']
        labels = {
            'diagnosis': 'Diagnostic', 'medications': 'Médicaments prescrits',
            'instructions': 'Instructions', 'follow_up_date': 'Date de suivi',
        }
        widgets = {
            'diagnosis':    forms.Textarea(attrs={'rows': 3}),
            'medications':  forms.Textarea(attrs={'rows': 4}),
            'instructions': forms.Textarea(attrs={'rows': 3}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model  = Review
        fields = ['rating', 'comment']
        labels = {'rating': 'Note (1-5)', 'comment': 'Commentaire'}
        widgets = {'comment': forms.Textarea(attrs={'rows': 3})}

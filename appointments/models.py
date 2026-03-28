from django.db import models
from django.conf import settings
from datetime import datetime


class TimeSlot(models.Model):
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='time_slots')
    date = models.DateField(verbose_name="Date")
    start_time = models.TimeField(verbose_name="Début")
    end_time = models.TimeField(verbose_name="Fin")
    is_booked = models.BooleanField(default=False, verbose_name="Réservé")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'start_time']
        unique_together = ['doctor', 'date', 'start_time']
        verbose_name = "Créneau"
        verbose_name_plural = "Créneaux"

    def __str__(self):
        return f"Dr.{self.doctor.last_name} | {self.date} {self.start_time}"

    def is_past(self):
        return datetime.combine(self.date, self.start_time) < datetime.now()


class Appointment(models.Model):
    STATUS_PENDING   = 'en_attente'
    STATUS_ACCEPTED  = 'accepte'
    STATUS_REJECTED  = 'refuse'
    STATUS_COMPLETED = 'termine'
    STATUS_CANCELLED = 'annule'

    STATUS_CHOICES = [
        (STATUS_PENDING,   'En attente'),
        (STATUS_ACCEPTED,  'Accepté'),
        (STATUS_REJECTED,  'Refusé'),
        (STATUS_COMPLETED, 'Terminé'),
        (STATUS_CANCELLED, 'Annulé'),
    ]

    patient   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_appointments')
    doctor    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_appointments')
    time_slot = models.OneToOneField(TimeSlot, on_delete=models.CASCADE, related_name='appointment')
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reason    = models.TextField(verbose_name="Motif")
    doctor_notes = models.TextField(blank=True, verbose_name="Notes médecin")
    booked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-booked_at']
        verbose_name = "Rendez-vous"
        verbose_name_plural = "Rendez-vous"

    def __str__(self):
        return f"RDV #{self.id} — {self.patient} → {self.doctor} [{self.get_status_display()}]"

    def can_be_cancelled(self):
        return self.status in [self.STATUS_PENDING, self.STATUS_ACCEPTED] and not self.time_slot.is_past()


class Prescription(models.Model):
    appointment  = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='prescription')
    diagnosis    = models.TextField(verbose_name="Diagnostic")
    medications  = models.TextField(blank=True, verbose_name="Médicaments")
    instructions = models.TextField(blank=True, verbose_name="Instructions")
    follow_up_date = models.DateField(blank=True, null=True, verbose_name="Date de suivi")
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ordonnance"
        verbose_name_plural = "Ordonnances"

    def __str__(self):
        return f"Ordonnance — {self.appointment.patient.get_full_name()}"


class Review(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='review')
    doctor  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_reviews')
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='given_reviews')
    rating  = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Avis"
        verbose_name_plural = "Avis"

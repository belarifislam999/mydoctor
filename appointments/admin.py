from django.contrib import admin
from .models import TimeSlot, Appointment, Prescription, Review

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'date', 'start_time', 'end_time', 'is_booked']
    list_filter  = ['is_booked', 'date']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'doctor', 'get_date', 'status', 'booked_at']
    list_filter  = ['status']
    def get_date(self, obj): return obj.time_slot.date
    get_date.short_description = 'Date RDV'

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'created_at']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'rating', 'created_at']

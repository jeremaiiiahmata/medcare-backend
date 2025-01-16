from django.contrib import admin
from .models import User, Profile, Patient, PrescriptionItem, Prescription, PreAssessment


# Register your models here.

class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email']

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'first_name', 'last_name']


admin.site.register(User, UserAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Patient)
admin.site.register(PrescriptionItem)
admin.site.register(Prescription)
admin.site.register(PreAssessment)

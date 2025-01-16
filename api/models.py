from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
# Create your models here.


class User (AbstractUser): #User model
    username = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username


class Profile(models.Model) :
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=75)
    middle_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    specialization = models.CharField(max_length=360, null=True, blank=True)
    contact_number = models.CharField(max_length=50)
    office_address = models.CharField(max_length=360, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to="user_images")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

def createUserProfile(sender, instance, created, **kwargs):

    if created : #Checks if the user created
        Profile.objects.create(user=instance) #Grab the profile object and creates a new one

def saveUserProfile(sender, instance, **kwargs):

    instance.profile.save()

post_save.connect(createUserProfile, sender=User)
post_save.connect(saveUserProfile, sender=User)

class Patient(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.CASCADE)  # Reference the custom User model
    image = models.ImageField(upload_to="patient_images/", null=True, blank=True)  # Allow image to be optional
    first_name = models.CharField(max_length=75)
    middle_name = models.CharField(max_length=50, null=True, blank=True)  # Optional middle name
    last_name = models.CharField(max_length=50)
    blood_type = models.CharField(max_length=3, null=True, blank=True)  # Validate blood types with choices
    email = models.EmailField(max_length=75, null=True, blank=True)  # Use EmailField for email validation
    contact_number = models.CharField(max_length=15, null=True, blank=True)  # Set a realistic length for phone numbers
    address = models.TextField(null=True, blank=True)  # Use TextField for potentially longer addresses
    age = models.PositiveIntegerField(null=True, blank=True)  # Age should be positive
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # Specify max_digits and decimal_places
    gender = models.CharField(max_length=10, null=True, blank=True)  # Use choices for consistency
    id_number = models.CharField(max_length=100, unique=True, null=True, blank=True)  # Add unique constraint for IDs
    allergies = models.TextField(null=True, blank=True)  # Already good for optional text

    def __str__(self):
        return f"{self.first_name} {self.last_name} (Doctor: {self.doctor.username})"

class Prescription(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.CASCADE)  # Reference the custom User model
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    date_created = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.first_name} {self.patient.last_name} (Created: {self.date_created})"

class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE)
    amount = models.CharField(max_length=50, blank=False)
    drug_name = models.CharField(max_length=50, blank=False)
    dosage = models.CharField(max_length=20, blank=False)
    frequency = models.CharField(max_length=100, blank=False)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"ID:{self.id} | [Drug Name : {self.drug_name} | Drug Amount : {self.amount}] - Prescription ID : {self.prescription.id} "

class PreAssessment(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.CASCADE)  # Reference the custom User model
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    date_created = models.DateField(auto_now_add=True)
    heart_rate = models.CharField(max_length=10, null=True, blank=True)
    temperature = models.CharField(max_length=20, null=True, blank=True)
    complaint = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    recommendations = models.TextField(null=True, blank=True)
    symptoms = models.TextField(null=True, blank=True)


    def __str__(self):
        return f"{self.patient} {self.date_created}"

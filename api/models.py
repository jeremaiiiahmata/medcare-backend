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
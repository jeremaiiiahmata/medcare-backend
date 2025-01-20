from rest_framework_simplejwt.views import TokenRefreshView
from django.urls import path
from . import views

urlpatterns = [
    path('token', views.MyTokenObtainPairView.as_view()), #use .as_view() for class based views
    path('token/refresh', TokenRefreshView.as_view()), #refreshes the token
    path('register', views.RegisterView.as_view()), #registers the user
    path('dashboard', views.dashboard), #function-based views
    path('profile', views.profile), #returns the profile
    path('patients', views.getPatients), #returns the patients of doctor
    path('patients/<int:id>', views.getPatientsByID), # returns the patient by ID
    path('create-patient', views.createPatient), # creates patients
    path('prescription/<int:id>', views.getPrescriptionByID),
    path('create-prescription', views.createPrescrption), # creates a prescription
    path('create-prescription/add-item', views.createPrescrptionItem), # creates an item in the prescription
    path('create-preassessment', views.createPreassessment), # creates a pre-assessment
]
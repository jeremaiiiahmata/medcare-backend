from rest_framework_simplejwt.views import TokenRefreshView
from django.urls import path
from . import views

urlpatterns = [
    path('token', views.MyTokenObtainPairView.as_view()), #use .as_view() for class based views
    path('token/refresh', TokenRefreshView.as_view()), #refreshes the token
    path('register', views.RegisterView.as_view()), #registers the user

    #-- User-related
    path('dashboard', views.dashboard), #function-based views
    path('profile', views.profile), #returns the profile

    #-- Patients
    path('patients', views.getPatients), #returns the patients of doctor
    path('patients/<int:id>', views.getPatientsByID), # returns the patient by ID
    path('create-patient', views.createPatient), # creates patients

    #Prescriptions
    path('prescriptions/<int:id>', views.getPrescriptions), #All prescriptions of patient
    path('prescription/<int:id>', views.getPrescriptionByID), #Prescription by ID
    path('create-prescription', views.createPrescrption), # creates a prescription

    #-- Prescription Item
    path('create-prescription-item/add', views.createPrescrptionItem), # creates an item in the prescription
    path('prescription-item/delete', views.removePrescriptionItem),

    path('create-preassessment', views.createPreassessment), # creates a pre-assessment
    path("generate-report/", views.ChatbotAPIView.as_view(), name="chat"),
]
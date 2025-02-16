from rest_framework_simplejwt.views import TokenRefreshView
from django.urls import path
from . import views

urlpatterns = [
    #use .as_view() for class based views
    #-- Authentication
    path('token', views.MyTokenObtainPairView.as_view()), #Login
    path('token/refresh', TokenRefreshView.as_view()), #refreshes the token
    path('register', views.RegisterView.as_view()), #registers the user

    #-- User-related
    path('dashboard', views.dashboard), #function-based views
    path('profile', views.profile), #returns the profile
    path('profile/edit', views.editProfile), #edits the profile

    #-- Patients
    path('patients', views.getPatients), #returns the patients of doctor
    path('patients/<int:id>', views.getPatientsByID), # returns the patient by ID
    path('create-patient', views.createPatient), # creates patients
    path('patient/delete', views.deletePatient),

    #Prescriptions
    path('prescriptions/<int:id>', views.getPrescriptions), #All prescriptions of patient, ID : id of patient
    path('prescription/<int:id>', views.getPrescriptionByID), #Prescription by ID
    path('prescription/create', views.createPrescrption), # creates a
    path('prescription/update', views.editPrescription), # edit prescription details
    path('prescription/delete', views.deletePrescription), #delete prescription

    #-- Prescription Item
    path('prescription-item/add', views.createPrescrptionItem), # creates an item in the prescription
    path('prescription-item/delete', views.removePrescriptionItem), #deletes an item in the prescription
    path('prescription-item/update', views.updatePrescriptionItem), #updates the item in the prescription

    #-- Pre-assessment
    path('pre-assessments', views.getPreAssessment), # get pre-assessment
    # path('pre-assessment) #get pre-assessment by ID
    path('pre-assessment/create', views.createPreassessment), #creates a pre-assessment
    path('pre-assessment/delete', views.deletePreassessment), #deletes pre-assessment

    #-- ChatGPT API
    path("generate-report/", views.ChatbotAPIView.as_view(), name="chat"),
]
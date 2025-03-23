from rest_framework_simplejwt.views import TokenRefreshView
from django.urls import path
from . import views
from .views import login_view, verify_otp, RequestOTPView, VerifyOTPView

urlpatterns = [
    #use .as_view() for class based views
    #-- Authentication
    path("token", login_view, name="token_obtain_pair"),  # Login with OTP support
    path("token/refresh", TokenRefreshView.as_view(), name="token_refresh"),  # Refresh token
    path("register", views.RegisterView.as_view(), name="register"),  # Register user
    path("request-otp", RequestOTPView.as_view(), name="request_otp"),  # Request OTP
    path("verify-otp", VerifyOTPView.as_view(), name="verify_otp"),  # Verify OTP

    #-- User-related
    path('dashboard', views.DashboardView.as_view()), #function-based views
    path('profile', views.profile), #returns the profile
    path('profile/edit', views.editProfile), #edits the profile

    #-- Patients
    path('patients', views.getPatients), #returns the patients of doctor
    path('patients/<int:id>', views.getPatientsByID), # returns the patient by ID
    path('create-patient', views.createPatient), # creates patients
    path('patient/edit', views.editPatient),
    path('patient/delete', views.deletePatient),

    #Prescriptions
    path('prescriptions/all', views.getAllPrescriptions),
    path('prescriptions/<int:id>', views.getPrescriptions), #All prescriptions of patient, ID : id of patient
    path('prescription-container/<int:id>', views.getSpecificPrescriptionContainer), #Prescription by ID
    path('prescription-items/<int:id>', views.getPrescriptionByID), #Prescription by ID
    path('prescription/create', views.createPrescription), # creates a
    path('prescription/update', views.editPrescription), # edit prescription details
    path('prescription/delete', views.deletePrescription), #delete prescription

    #-- Prescription Item
    path('prescription-item/add', views.createPrescriptionItem), # creates an item in the prescription
    path('prescription-item/delete', views.removePrescriptionItem), #deletes an item in the prescription
    path('prescription-item/update', views.updatePrescriptionItem), #updates the item in the prescription

    #-- Pre-assessment
    path('pre-assessments/all', views.getAllPreAssessment), # get pre-assessment
    path('pre-assessments', views.getPreAssessment), # get pre-assessment
    path('pre-assessment', views.getPreAssessmentByID), #get pre-assessment by ID
    path('pre-assessment/create', views.createPreassessment), #creates a pre-assessment
    path('pre-assessment/delete', views.deletePreassessment), #deletes pre-assessment

    #-- ChatGPT API
    path("generate-report/", views.ChatbotAPIView.as_view(), name="chat"),
]
from django.core.serializers import serialize
from django.shortcuts import render
from collections import Counter
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from api.models import Profile, User, Patient, Prescription, PrescriptionItem, DrugInteractions, PreAssessment, \
    DrugAvailableDosages, GeneratedReport
from api.serializers import UserSerializer, MyTokenObtainPairSerializer, RegisterSerializer, PatientSerializer, \
    PrescriptionSerializer, PreassessmentSerializer, ProfileSerializer, PrescriptionItemSerializer, ChatbotSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Avg, Q
from datetime import timedelta, datetime
import os
import openai
from asgiref.sync import sync_to_async, async_to_sync  # Fix async/sync issue
from django.db.models import Q
from django.core.cache import cache  # Caching for faster responses
import logging
import hashlib
import random
import smtplib
from django.conf import settings
from django.core.mail import send_mail
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils.timezone import now
from datetime import timedelta
from .models import User
from .serializers import RegisterSerializer


# ✅ Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Store OTPs temporarily
OTP_EXPIRATION_TIME = timedelta(minutes=5)
otp_storage = {}  # Example: { "user@example.com": { "otp": "123456", "expires_at": timestamp } }

# Create your views here.

class MyTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.user

        # 🔹 Step 1: Check if 2FA is enabled
        if user.is_2fa_enabled:
            otp = request.data.get("otp")  # 🔥 OTP sent from frontend

            # 🔹 Step 2: If no OTP is provided, ask for it
            if not otp:
                return Response(
                    {"otp_required": True, "message": "OTP has been sent to your email."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # 🔹 Step 3: Validate OTP
            if not user.verify_otp(otp):
                return Response(
                    {"error": "Invalid OTP. Please try again."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 🔹 Step 4: Generate and return JWT tokens
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class RegisterView(generics.CreateAPIView): #creates a user
    queryset = User.objects.all()
    permission_classes = (AllowAny,) #Allows everyone to access this view
    serializer_class = RegisterSerializer #sets the serializer class to the RegisterSerializer we created

class RequestOTPView(generics.GenericAPIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(email=email, password=password)
        if not user:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # 🔹 Use the generate_otp() method in the User model
        otp = user.generate_otp()

        # Send OTP via email
        send_mail(
            "Your OTP Code",
            f"Your OTP code is {otp}. It will expire in 5 minutes.",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

        return Response({"message": "OTP sent to your email"}, status=status.HTTP_200_OK)


class VerifyOTPView(generics.GenericAPIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        print(f"🔍 Received email: {email}, OTP: {otp}")  # Debugging

        try:
            user = User.objects.get(email=email)
            print(f"🔍 Found user: {user.email}, Stored OTP: {user.otp}")  # Debugging
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        if user.verify_otp(str(otp)):  # Ensure OTP is treated as a string
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }, status=status.HTTP_200_OK)

        return Response({"error": "Invalid or expired OTP"},
                        status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def login_view(request):
    email = request.data.get("email")
    password = request.data.get("password")
    user = authenticate(email=email, password=password)

    if user is None:
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

    # If 2FA is enabled, send OTP instead of issuing JWT tokens
    if user.is_2fa_enabled:
        otp = user.generate_otp()

        # Send OTP via email (Modify for SMS if needed)
        send_mail(
            "Your OTP Code",
            f"Your OTP code is {otp}. It will expire in 5 minutes.",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,    
        )

        return Response({
            "detail": "2FA required. OTP has been sent to your email.",
            "otp_required": True
        }, status=status.HTTP_401_UNAUTHORIZED)

    # Issue JWT tokens if 2FA is NOT enabled
    refresh = RefreshToken.for_user(user)
    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    })

@api_view(["POST"])
def verify_otp(request):
    email = request.data.get("email")  # Fix: Ensure email is received
    otp_code = request.data.get("otp")

    try:
        user = User.objects.get(email=email)
        if user.verify_otp(otp_code):
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            })
        return Response({"detail": "Invalid or expired OTP"}, status=status.HTTP_401_UNAUTHORIZED)

    except User.DoesNotExist:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    except User.DoesNotExist:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = datetime.today()
        six_months_ago = today - timedelta(days=180)
        first_day_of_current_month = today.replace(day=1)
        first_day_of_last_month = (first_day_of_current_month - timedelta(days=1)).replace(day=1)

        doctor_id = request.user.id

        total_patients = Patient.objects.filter(doctor=doctor_id).count()
        total_prescriptions = Prescription.objects.filter(doctor=doctor_id).count()
        total_pre_assessments = PreAssessment.objects.filter(doctor=doctor_id).count()
        total_drug_interactions = DrugInteractions.objects.count()

        # Last Month's Counts
        last_month_patients = Patient.objects.filter(
            doctor=doctor_id, date_created__gte=first_day_of_last_month, date_created__lt=first_day_of_current_month
        ).count()
        last_month_prescriptions = Prescription.objects.filter(
            doctor=doctor_id, date_created__gte=first_day_of_last_month, date_created__lt=first_day_of_current_month
        ).count()
        last_month_pre_assessments = PreAssessment.objects.filter(
            doctor=doctor_id, date_created__gte=first_day_of_last_month, date_created__lt=first_day_of_current_month
        ).count()

        # Calculate Growth Percentage
        def calculate_growth(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0  # Avoid division by zero
            return round(((current - previous) / previous) * 100, 2)

        patient_growth = calculate_growth(total_patients, last_month_patients)
        prescription_growth = calculate_growth(total_prescriptions, last_month_prescriptions)
        pre_assessment_growth = calculate_growth(total_pre_assessments, last_month_pre_assessments)

        # Active and Inactive Patients
        active_patients = Patient.objects.filter(
            Q(preassessment__date_created__gte=six_months_ago) |
            Q(prescription__date_created__gte=six_months_ago)
        ).distinct().count()
        inactive_patients = total_patients - active_patients

        # Doctor Workload Insights
        doctor_workload = (
            User.objects.annotate(
                prescription_count=Count("prescription"),
                preassessment_count=Count("preassessment")
            ).values("username", "prescription_count", "preassessment_count")
        )
        doctor_workload = [
            {"doctor": d["username"], "prescriptions": d["prescription_count"], "assessments": d["preassessment_count"]}
            for d in doctor_workload
        ]

        # Most Frequent Drug Interactions
        common_drug_interactions = (
            DrugInteractions.objects.values("drug_a", "drug_b")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )
        common_drug_interactions = [
            {"drug_a": di["drug_a"], "drug_b": di["drug_b"], "count": di["count"]}
            for di in common_drug_interactions
        ]

        # Patients with Chronic Conditions
        chronic_conditions_count = PreAssessment.objects.exclude(chronic_conditions="").count()

        # Average Age of Patients
        average_patient_age = (
                Patient.objects.filter(doctor=doctor_id).aggregate(Avg("age"))["age__avg"] or 0
        )

        # Monthly Prescription Trends
        monthly_prescriptions = (
            Prescription.objects
            .values("date_created__month", "date_created__year")
            .annotate(count=Count("id"))
            .order_by("-date_created__year", "-date_created__month")[:6]
        )
        monthly_prescription_trend = [
            {"month": f"{p['date_created__year']}-{p['date_created__month']}", "count": p["count"]}
            for p in monthly_prescriptions
        ]

        # Most Diagnosed Conditions (Chronic Conditions)
        top_diagnosed_conditions = (
            PreAssessment.objects.exclude(chronic_conditions="")
            .values("chronic_conditions")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )
        top_diagnosed_conditions = [
            {"condition": c["chronic_conditions"], "count": c["count"]} for c in top_diagnosed_conditions
        ]

        # Prescription Completion Rate (Patients who had multiple prescriptions or follow-ups)
        total_follow_ups = Prescription.objects.filter(patient__prescription__isnull=False).count()
        prescription_completion_rate = round((total_follow_ups / total_prescriptions) * 100, 2) if total_prescriptions else 0

        # Fetch 5 Most Recent Patients Created by the Doctor
        recent_patients = Patient.objects.filter(doctor=doctor_id).order_by("-date_created", "-time_created")[:6]
        recent_patients_serialized = PatientSerializer(recent_patients, many=True).data

        # Most Prescribed Medications
        prescribed_drugs = (
            PrescriptionItem.objects
            .filter(prescription__doctor=doctor_id)
            .values_list("drug_name", flat=True)
        )

        # Count occurrences & get top 3
        top_3_prescribed = [drug for drug, count in Counter(prescribed_drugs).most_common(3)]

        #Doctor
        doctor = User.objects.get(id=doctor_id)
        greeting = f"Hello, {doctor.username}"

        # Structure the response
        data = {
            "total_patients": {"count": total_patients, "growth": patient_growth},
            "total_prescriptions": {"count": total_prescriptions, "growth": prescription_growth},
            "total_pre_assessments": {"count": total_pre_assessments, "growth": pre_assessment_growth},
            "total_drug_interactions": total_drug_interactions,
            "active_patients": active_patients,
            "inactive_patients": inactive_patients,
            "doctor_workload": doctor_workload,
            "recent_patients" : recent_patients_serialized,
            "common_drug_interactions": common_drug_interactions,
            "chronic_conditions_count": chronic_conditions_count,
            "average_patient_age": int(average_patient_age),
            "monthly_prescription_trend": monthly_prescription_trend,
            "top_diagnosed_conditions": top_diagnosed_conditions,
            "prescription_completion_rate": prescription_completion_rate,
            "top_3_prescribed_medications": top_3_prescribed,
            "greeting": greeting
        }

        return Response(data)

# GET : Get the user's details
@api_view(['GET']) #defining the methods
@permission_classes([IsAuthenticated]) #defining the permission in function based classes
def profile(request):

    user_id = request.user.id

    profile = Profile.objects.get(id=user_id)
    serializer = ProfileSerializer(profile)

    return Response({"status": "success", "data": serializer.data})

@api_view(['PUT'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def editProfile(request):

    user_ID = request.user.id
    print("Request Data", request.data)

    profile = get_object_or_404(Profile, id=user_ID)
    serializer = ProfileSerializer(profile, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

    return Response({"status": "error", "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


# POST: Create Patient
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def createPatient(request):

    user_ID = request.user.id

    # Ensure the doctor exists
    doctor = User.objects.get(id=user_ID)
    serializer = PatientSerializer(data=request.data)

    try:
        # Validate the data
        if serializer.is_valid():
            serializer.save(doctor=doctor)  # Save the patient with the associated doctor
            return Response({
                "status": "success",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "status": "error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            print(serializer.errors)

    except User.DoesNotExist:
        return Response({"status": "error", "message": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)


# GET: Query Patients by Doctor
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def getPatients(request):

    doctor_id = request.user.id  # Use query params for filtering

    if not doctor_id:
        return Response({"status": "error", "message": "Doctor ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Ensure the doctor exists
        doctor = User.objects.get(id=doctor_id)

        # Get all patients for the doctor
        patients = Patient.objects.filter(doctor=doctor)

        paginator = LimitOffsetPagination()
        paginated_patients = paginator.paginate_queryset(patients, request)

        serializer = PatientSerializer(paginated_patients,many=True)

        return paginator.get_paginated_response(serializer.data)
      
        patients = Patient.objects.filter(doctor=doctor).values(
            'id', 'first_name', 'last_name', 'blood_type', 'email', 'contact_number', 'street_name',
            'city', 'state_province', 'postal_code', 'age', 'weight', 'gender', 'id_number', 'allergies'
        )

        # return Response({"status": "success", "data": patients}, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response({"status": "error", "message": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Patients by ID
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def getPatientsByID(request, id):

    doctorID = request.user.id

    # Ensure the doctor exists and get the patient
    patient = get_object_or_404(Patient, id=id, doctor_id=doctorID)

    serializer = PatientSerializer(patient)
    return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

# EDIT: Remove Prescription Items of Patient
@api_view(['PUT'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def editPatient(request):

    patient_id = request.query_params.get("patient_id")


    patient = get_object_or_404(Patient, id=patient_id)
    serializer = PatientSerializer(patient, data=request.data, partial=True)

    try :
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"status": "error", "message": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



# DELETE: Remove Prescription Items of Patient
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def deletePatient(request):

    patient_id = request.query_params.get("patient_id")

    patient = get_object_or_404(Patient, id=patient_id)
    patient.delete()
    return Response({"status": "success", "message": "Patient item deleted successfully."}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def getAllPrescriptions(request):

    doctor_id = request.user.id

    doctor = User.objects.get(id=doctor_id)

    # Fetch all prescriptions belonging to the logged-in doctor and the given patient
    prescriptions = Prescription.objects.filter(doctor_id=doctor_id)

    if not prescriptions.exists():
        return Response({"status": "error", "message": "No prescriptions found for this doctor."},
                        status=status.HTTP_404_NOT_FOUND)

    paginator = LimitOffsetPagination()
    paginated_prescriptions = paginator.paginate_queryset(prescriptions, request)

    serializer = PrescriptionSerializer(paginated_prescriptions,many=True)

    return paginator.get_paginated_response(serializer.data)



# Prescriptions
@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def getPrescriptions(request, id):

    doctor_id = request.user.id

    # Fetch all prescriptions belonging to the logged-in doctor and the given patient
    prescriptions = Prescription.objects.filter(patient_id=id, doctor_id=doctor_id)

    if not prescriptions.exists():
        return Response({"status": "error", "message": "No prescriptions found for this patient."},
                        status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        prescriptions.delete()
        return Response({"status": "success", "message": "Prescriptions deleted successfully."},
                        status=status.HTTP_200_OK)

    serializer = PrescriptionSerializer(prescriptions, many=True)  # Use many=True for multiple objects
    return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

# Prescriptions
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def getSpecificPrescriptionContainer(request, id):

    prescription_ID = id

    # Fetch all prescriptions belonging to the logged-in doctor and the given patient
    prescription = Prescription.objects.get(id=prescription_ID)
    print(prescription)


    serializer = PrescriptionSerializer(prescription, )  # Use many=True for multiple objects
    return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createPrescription(request):
    user_id = request.user.id  # Get doctor ID
    patient_id = request.query_params.get('patient_id')  # Get patient ID
    pre_assessment_id = request.query_params.get('pre_assessment_id')  # Get pre-assessment ID (optional)

    try:
        if not patient_id:
            return Response(
                {"status": "error", "message": "Patient ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch the patient
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {"status": "error", "message": "Patient not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Fetch the specific pre-assessment if provided
        pre_assessment = None
        if pre_assessment_id:
            try:
                pre_assessment = PreAssessment.objects.get(id=pre_assessment_id, patient=patient)
            except PreAssessment.DoesNotExist:
                return Response(
                    {"status": "error", "message": "Pre-Assessment not found for this patient."},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Extract prescription data from request
        data = request.data.copy()
        data.pop('doctor', None)
        data.pop('patient', None)
        data.pop('date_created', None)

        serializer = PrescriptionSerializer(data=data)

        if serializer.is_valid():
            # Save the prescription
            prescription = serializer.save(
                doctor=request.user,
                patient=patient
            )

            # If a valid pre-assessment is provided, link it to the new prescription
            if pre_assessment:
                pre_assessment.prescription = prescription
                pre_assessment.save()
                print("Pre-assessment created successfully!")

            return Response({
                "status": "success",
                "message": f"Prescription created successfully for patient {patient.first_name} {patient.last_name}.",
                "prescription": serializer.data
            }, status=status.HTTP_201_CREATED)

        else:
            return Response({
                "status": "error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response(
            {"status": "error", "message": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# PUT: Update Prescription of Patient
@api_view(['PUT'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def editPrescription(request):

    prescription_id = request.query_params.get("prescription_id")
    print(request.data)

    prescription = get_object_or_404(Prescription, id=prescription_id)
    serializer = PrescriptionSerializer(prescription, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

    return Response({"status": "error", "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

# PUT: Update Prescription of Patient
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def deletePrescription(request):

    prescription_id = request.query_params.get("prescription_id")
    print(request.data)

    prescription = get_object_or_404(Prescription, id=prescription_id)
    prescription.delete()

    return Response({"status": "success", "message": "Prescription deleted successfully!"}, status=status.HTTP_200_OK)

# GET: GET Preassessments of Patient
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def getAllPreAssessment(request):
    doctor_id = request.user.id

    doctor = User.objects.get(id=doctor_id)

    # Fetch all prescriptions belonging to the logged-in doctor and the given patient
    preassessments = PreAssessment.objects.filter(doctor_id=doctor_id)

    if not preassessments.exists():
        return Response({"status": "error", "message": "No pre-assessments found for this doctor."},
                        status=status.HTTP_404_NOT_FOUND)

    paginator = LimitOffsetPagination()
    paginated_preassessments = paginator.paginate_queryset(preassessments, request)

    serializer = PreassessmentSerializer(paginated_preassessments, many=True)

    return paginator.get_paginated_response(serializer.data)


# GET: GET Preassessments of Patient
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def getPreAssessment(request):

    patient_id = request.query_params.get('patient_id')  # Get the prescription ID from query params

    # Validate if the patient ID is provided
    if not patient_id:
        return Response({"status": "error", "message": "Patient ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Fetch doctor (logged-in user) and patient from the database
        preassessments = PreAssessment.objects.filter(patient=patient_id)

        if not preassessments.exists():
            return Response({"status": "error", "message": "No pre-assessments found for this patient."},
                            status=status.HTTP_404_NOT_FOUND)

        serializer = PreassessmentSerializer(preassessments, many=True)
        print("Preassessment fetched.")
        print(f"{serializer.data}")

        return Response({"status": "success", "data": serializer.data})

    except User.DoesNotExist:
        return Response({"status": "error", "message": "Prescription ID not found"},
                        status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# GET: GET Preassessments of Patient
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def getPreAssessmentByID(request):

    pre_assessmentID = request.query_params.get('pre_assessmentID')  # Get the patient ID from query params

    if not pre_assessmentID:
        return Response({"status": "error", "message": "Pre-assessment ID is required."},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        pre_assessment = get_object_or_404(PreAssessment, id=pre_assessmentID)
        serializer = PreassessmentSerializer(pre_assessment)
        return Response({"status" : "success", "data" : serializer.data})

    except User.DoesNotExist:
        return Response({"status": "error", "message": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)

    except User.DoesNotExist:
        return Response({"status": "error", "message": "Prescription ID not found"},
                        status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# POST: Create Prescription Item of Patient
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def createPrescriptionItem(request):
    prescription_id = request.query_params.get('prescription_id')  # Get the prescription ID from query params

    # Validate if the patient ID is provided
    if not prescription_id:
        return Response({"status": "error", "message": "Prescription ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:

        # Fetch doctor (logged-in user) and patient from the database
        prescription = Prescription.objects.get(id=prescription_id)

        # Add doctor and patient to request data
        data = request.data.copy()
        data['prescription'] = prescription.id

        # Serialize and validate data
        serializer = PrescriptionItemSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": "success",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "status": "error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    except User.DoesNotExist:
        return Response({"status": "error", "message": "Prescription ID not found"},
                        status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createPreassessment(request):
    user_id = request.user.id  # Get doctor ID
    prescription_id = request.query_params.get('prescription_id')  # Get prescription ID (optional)

    try:
        prescription = None  # Default to None if no prescription ID is provided
        patient = None  # Default patient to None

        # If prescription_id is provided, try fetching it
        if prescription_id:
            try:
                prescription = Prescription.objects.get(id=prescription_id)
                patient = prescription.patient  # Get the patient from the prescription
            except Prescription.DoesNotExist:
                return Response({"status": "error", "message": "Prescription not found."},
                                status=status.HTTP_404_NOT_FOUND)

        # If no prescription, expect a patient ID in request body
        if not prescription:
            patient_id = request.query_params.get('patient_id')
            if not patient_id:
                return Response({"status": "error", "message": "Either Prescription ID or Patient ID is required."},
                                status=status.HTTP_400_BAD_REQUEST)

            try:
                patient = Patient.objects.get(id=patient_id)
            except Patient.DoesNotExist:
                return Response({"status": "error", "message": "Patient not found."},
                                status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data.pop('patient', None)
        data.pop('doctor', None)

        serializer = PreassessmentSerializer(data=data)

        if serializer.is_valid():
            pre_assessment = serializer.save(
                prescription=prescription,  # Link if available, else None
                patient=patient,  # Assign patient
                doctor=request.user  # Assign doctor
            )
            return Response({
                "status": "success",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)

        else:
            return Response({"status": "error", "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({"status": "error", "message": str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# DELETE: Remove Pre-assessment of Patient
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def deletePreassessment(request):

    pre_assessmentID = request.query_params.get('pre_assessmentID')  # Get the patient ID from query params
    print(pre_assessmentID)
    print("Deleting...")

    if not pre_assessmentID:
        return Response({"status": "error", "message": "Pre-assessment ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        pre_assessment = get_object_or_404(PreAssessment, id=pre_assessmentID)
        print(pre_assessment)
        pre_assessment.delete()
        print("Deleted.")
        return Response({"status": "error", "message": "Pre-assessment has been successfully deleted."}, status=status.HTTP_200_OK)

    except Exception as e:
        print("Error")
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# GET: GET Prescription Items of Patient
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def getPrescriptionByID(request, id): # ID here pertains to the prescriptionID

   try:

       prescription = PrescriptionItem.objects.filter(prescription=id).values(
            'id', 'dosage', 'amount', 'drug_name', 'frequency', 'notes'
        )

       return Response({"status" : "success", "data" : list(prescription)})

   except User.DoesNotExist:
       return Response({"status": "error", "message": "Doctor or Patient not found."}, status=status.HTTP_404_NOT_FOUND)

   except Exception as e:
       return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# DELETE: Remove Prescription Items of Patient
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def removePrescriptionItem(request):

    prescription_id = request.query_params.get("prescription_id")
    drug_id = request.query_params.get("drug_id")

    prescription_item = get_object_or_404(PrescriptionItem, id=drug_id, prescription=prescription_id)
    prescription_item.delete()
    return Response({"status": "success", "message": "Prescription item deleted successfully."}, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def updatePrescriptionItem(request):

    prescription_id = request.data.get("prescription_id")
    item_id = request.data.get("id")

    if not prescription_id or not item_id:
        return Response(
            {"status": "error", "message": "prescription_id and item_id are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    prescription_item = get_object_or_404(PrescriptionItem, id=item_id, prescription=prescription_id)
    serializer = PrescriptionItemSerializer(prescription_item, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

    return Response({"status": "error", "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

# Load OpenAI API Key from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

class ChatbotAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    def post(self, request):
        """Process prescription interactions efficiently and query GPT-4."""

        try:
            # ✅ Fetch Prescription, Patient, and Medications in ONE Query (Synchronous ORM)
            prescription_id = request.query_params.get("prescription_id")
            prescription = Prescription.objects.select_related("patient").prefetch_related("prescriptionitem_set").get(id=prescription_id)
            preassessment = PreAssessment.objects.filter(prescription=prescription).first()
            print(preassessment)
            patient = prescription.patient
            items = list(prescription.prescriptionitem_set.all())  # Convert QuerySet to list for faster access
        except Prescription.DoesNotExist:
            return Response({"error": "Prescription not found."}, status=status.HTTP_404_NOT_FOUND)

        # ✅ Extract Patient Information
        patient_info = {
            "age": patient.age,
            "weight": f"{patient.weight} kg",
            "allergies" : patient.allergies
        }

        # ✅ Extract Prescribed Medications List
        prescribed_medications = {
            item.drug_name: {"dosage": item.dosage, "frequency": item.frequency, "amount": item.amount}
            for item in items
        }

        # Extract Patient's Assessments
        assessments = None
        if preassessment:
            assessments = {
                "blood_pressure": preassessment.blood_pressure,
                "heart_rate": preassessment.heart_rate,
                "temperature": preassessment.temperature,
                "chronic_conditions": preassessment.chronic_conditions,
                "medical_history": preassessment.medical_history,
                "smoking_history": preassessment.smoking_history,
                "alcohol_consumption_history": preassessment.alcohol_consumption_history,
                "complaint": preassessment.complaint
            }

        print(f"This is the assessment {assessments}")


        # ✅ Generate a hash for the prescription to ensure uniform responses
        prescription_str = str(sorted(prescribed_medications.items()))
        prescription_hash = hashlib.sha256(prescription_str.encode()).hexdigest()

        # ✅ Check if the report is already stored in the database
        stored_report = GeneratedReport.objects.filter(prescription_hash=prescription_hash).first()
        if stored_report:
            logger.info(f"Stored report found for prescription hash {prescription_hash}, returning cached report.")
            return Response({"reply": stored_report.response}, status=status.HTTP_200_OK)

        # Get all prescribed drugs
        prescribed_drug_names = list(prescribed_medications.keys())

        # ✅ Retrieve Available Market Dosages from Database
        available_dosages = {dosage.drug_name: dosage.available_dosage for dosage in
                             DrugAvailableDosages.objects.filter(drug_name__in=prescribed_medications.keys())}

        # ✅ Optimize Interaction Query (Avoid Slow `__in` Queries)
        known_drugs = set(DrugInteractions.objects.values_list("drug_a", flat=True)) | set(
            DrugInteractions.objects.values_list("drug_b", flat=True))

        missing_drugs = [
            {"drug": drug, "reason": "Not found in the local database, requires external validation"}
            for drug in prescribed_medications.keys() if drug not in known_drugs
        ]

        # Query only interactions where both drugs exist in the prescribed list
        interactions = list(DrugInteractions.objects.filter(
            (Q(drug_a__in=prescribed_drug_names) & Q(drug_b__in=prescribed_drug_names)) |
            (Q(drug_b__in=prescribed_drug_names) & Q(drug_a__in=prescribed_drug_names))  # Handles swapped order
        ).values("drug_a", "drug_b", "severity", "description", "management"))

        # ✅ Shorten the GPT-4 Prompt to Reduce Token Usage
        prompt = f"""
               **Instructions:**
                - Help the doctor detect **ALL potential drug-drug interactions**, including **previously detected ones**.
                - Recommend **dosage adjustments** only if necessary, ensuring recommendations follow standard dosages.
                - Ensure dosage recommendations align with **verified market dosages**, using this dataset: {available_dosages}.
                - If no market dosage is found, attempt to determine a safe alternative.
                - If a drug is missing from the known interactions database, use online sources to analyze its interactions.
                - You can use the assessment data to make any changes or consideration in dosage and drugs prescribed.
                - For the reason in dosage recommendations, state the reason WHY (does it have the wrong dosage or is the frequency wrong?) don't include anything market related in the reason part.

               **Patient Info:** Age: {patient_info["age"]}, Weight: {patient_info["weight"]}, Allergens: {patient_info["allergies"]}
               
                **Patient's Assessment:** {"No assessment data available." if not assessments else 
                   f"Heart Rate: {assessments.get('heart_rate', 'N/A')}, " +
                   f"Temperature: {assessments.get('temperature', 'N/A')}, " +
                   f"Blood Pressure: {assessments.get('blood_pressure', 'N/A')}, " +
                   f"Medical History: {assessments.get('medical_history', 'N/A')}, " +
                   f"Chronic Conditions: {assessments.get('chronic_conditions', 'N/A')}, " +
                   f"Smoking History: {assessments.get('smoking_history', 'N/A')}, " +
                   f"Alcohol Consumption History: {assessments.get('alcohol_consumption_history', 'N/A')}, " +
                   f"Complaint: {assessments.get('complaint', 'N/A')}"
                }

                

               **Medications:** {', '.join([f"{med} ({data['dosage']})" for med, data in prescribed_medications.items()])}

               **Interactions from Database:** {interactions if interactions else "No interactions detected."}
               
               **Market Dosages Reference:** {available_dosages if available_dosages else "No database record found. Use online sources if needed."}
               
               **Missing Drugs (Require Online Search):** {missing_drugs if missing_drugs else "All drugs are in the database."}

               **Instructions:**
                - List drug interactions **with medical explanations**.
                - Suggest dosage adjustments only if the prescribed dose **is outside the normal range**.
                - **DO NOT** introduce randomness—ensure that identical prescriptions receive **identical responses**.
                - **Strictly follow predefined dosage recommendations** (if not provided from the database, use external reliable sources).
                - Also, use external sources to check for the frequency of the medicine. Make sure it does not overdose the patient.
                - If severity is `"None"`, **omit it from the response**.
                - If a drug is missing from the database, use external reliable sources to check its interactions.
                - Output in **structured JSON format** only.

               **STRICTLY FOLLOW THIS JSON FORMAT:**
               {{
                   "interactions": [{{"drug_a": "", "drug_b": "", "severity": "", "description": "", "management": ""}}],
                   "dosage_adjustments": [{{"drug": "", "current": "", "recommended": "",  "reason": ""}}],
                   "final_recommendation": ""
               }}
               """

        # ✅ Check if cached GPT-4 response exists
        cache_key = f"gpt_response_{prescription_id}_{hash(str(prescribed_medications))}"
        cached_response = cache.get(cache_key)

        if cached_response:
            return Response({"reply": cached_response}, status=status.HTTP_200_OK)

        # ✅ Call GPT-4 Synchronously Using `async_to_sync`
        try:
            chatbot_reply = async_to_sync(self.query_gpt4)(prompt)

            # ✅ Store the generated report in the database
            GeneratedReport.objects.create(prescription_hash=prescription_hash, response=chatbot_reply)

            logger.info(f"GPT-4 API called for prescription hash {prescription_hash}. Response stored.")
            return Response({"reply": chatbot_reply}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"GPT-4 API error for prescription hash {prescription_hash}: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def query_gpt4(self, prompt):
        """Async function to query GPT-4 and return the response."""
        client = openai.OpenAI()
        response = await sync_to_async(client.chat.completions.create)(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system",
                 "content": "You are a medical AI providing structured prescription analysis, ensuring compliance with market dosages."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            top_p=1,
            max_tokens=2000
        )
        logger.info(f"GPT-4 response generated. Token usage: {len(response.choices[0].message.content.split())} words.")
        return response.choices[0].message.content


from django.core.serializers import serialize
from django.shortcuts import render
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from api.models import Profile, User, Patient, Prescription, PrescriptionItem, DrugInteractions, PreAssessment
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

# Create your views here.

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer #sets the serializer class to the MyTokenObtainPairSerializer we created

class RegisterView(generics.CreateAPIView): #creates a user
    queryset = User.objects.all()
    permission_classes = (AllowAny,) #Allows everyone to access this view
    serializer_class = RegisterSerializer #sets the serializer class to the RegisterSerializer we created

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = datetime.today()
        six_months_ago = today - timedelta(days=180)

        # Total counts
        total_doctors = User.objects.count()
        total_patients = Patient.objects.count()
        total_prescriptions = Prescription.objects.count()
        total_pre_assessments = PreAssessment.objects.count()
        total_drug_interactions = DrugInteractions.objects.count()

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

        # Most Common Symptoms
        symptom_counts = (
            PreAssessment.objects.exclude(symptoms="")
            .values("symptoms")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )
        most_common_symptoms = [
            {"symptom": s["symptoms"], "count": s["count"]} for s in symptom_counts
        ]

        # Average Age of Patients
        average_patient_age = Patient.objects.aggregate(Avg("age"))["age__avg"] or 0

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

        # Structure the response
        data = {
            "total_doctors": total_doctors,
            "total_patients": total_patients,
            "total_prescriptions": total_prescriptions,
            "total_pre_assessments": total_pre_assessments,
            "total_drug_interactions": total_drug_interactions,
            "active_patients": active_patients,
            "inactive_patients": inactive_patients,
            "doctor_workload": doctor_workload,
            "common_drug_interactions": common_drug_interactions,
            "chronic_conditions_count": chronic_conditions_count,
            "most_common_symptoms": most_common_symptoms,
            "average_patient_age": average_patient_age,
            "monthly_prescription_trend": monthly_prescription_trend,
            "top_diagnosed_conditions": top_diagnosed_conditions,
            "prescription_completion_rate": prescription_completion_rate,
        }

        return Response(data)


# GET : Fetch the dashboard
@api_view(['GET']) #defining the methods
@permission_classes([IsAuthenticated]) #defining the permission in function based classes
def dashboard(request):

    doctor_id = request.user.id

    """
       Returns an overview of the system's data, including total counts for key models.
       """
    user = request.user  # Get the authenticated user

    # Count only the data relevant to the logged-in doctor
    total_patients = Patient.objects.filter(doctor=doctor_id).count()
    total_prescriptions = Prescription.objects.filter(doctor=doctor_id).count()
    total_pre_assessments = PreAssessment.objects.filter(doctor=doctor_id).count()
    total_drug_interactions = DrugInteractions.objects.count()  # Global count

    # Response data
    data = {
        "total_patients": total_patients,
        "total_prescriptions": total_prescriptions,
        "total_pre_assessments": total_pre_assessments,
        "total_drug_interactions": total_drug_interactions,
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
        patients = Patient.objects.filter(doctor=doctor).values(
            'id', 'first_name', 'last_name', 'blood_type', 'email', 'contact_number', 'address', 'age', 'weight', 'gender', 'id_number', 'allergies'
        )

        return Response({"status": "success", "data": list(patients)}, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response({"status": "error", "message": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Patients
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def getPatientsByID(request, id):

    doctorID = request.user.id

    # Ensure the doctor exists and get the patient
    patient = get_object_or_404(Patient, id=id, doctor_id=doctorID)

    if request.method == 'DELETE':
        patient.delete()
        return Response({"status": "success", "message": "Patient deleted successfully."}, status=status.HTTP_200_OK)

    serializer = PatientSerializer(patient)
    return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

# DELETE: Remove Prescription Items of Patient
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def deletePatient(request):

    patient_id = request.data.get("patient_id")

    patient = get_object_or_404(Patient, id=patient_id)
    patient.delete()
    return Response({"status": "success", "message": "Patient item deleted successfully."}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def getAllPrescriptions(request):

    doctor_id = request.user.id

    # Fetch all prescriptions belonging to the logged-in doctor and the given patient
    prescriptions = Prescription.objects.filter(doctor_id=doctor_id)

    if not prescriptions.exists():
        return Response({"status": "error", "message": "No prescriptions found for this doctor."},
                        status=status.HTTP_404_NOT_FOUND)

    serializer = PrescriptionSerializer(prescriptions, many=True)  # Use many=True for multiple objects
    return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

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


# POST: Create Prescription of Patient
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def createPrescription(request):
    user_id = request.user.id  # Get the authenticated doctor's ID
    patient_id = request.query_params.get('patient_id')  # Get the patient ID from query params

    # Validate if the patient ID is provided
    if not patient_id:
        return Response({"status": "error", "message": "Patient ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Fetch doctor (logged-in user) and patient from the database
        doctor = User.objects.get(id=user_id) #Gets the current doctor's information
        patient = Patient.objects.get(id=patient_id) #Gets the patient based on ID from params

        # Create the Prescription instance
        prescription = Prescription(doctor=doctor, patient=patient)
        prescription.save()

        return Response({
            "status": "success",
            "message": f"Prescription created successfully for patient {patient.first_name} {patient.last_name}. Doctor : {doctor.username}",
            "prescription_id": prescription.id  # Return the prescription ID if needed
        }, status=status.HTTP_201_CREATED)

    except User.DoesNotExist:
        return Response({"status": "error", "message": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)

    except Patient.DoesNotExist:
        return Response({"status": "error", "message": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"status": "error", "message": f"An unexpected error occurred: {str(e)}"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

    try:
        # Fetch doctor (logged-in user) and patient from the database
        preassessments = PreAssessment.objects.filter(doctor=doctor_id)

        if not preassessments.exists():
            return Response({"status": "error", "message": "No pre-assessments found for this doctor."},
                            status=status.HTTP_404_NOT_FOUND)

        serializer = PreassessmentSerializer(preassessments, many=True)
        print("Preassessment fetched.")
        print(f"{serializer.data}")

        return Response({"status": "success", "data": serializer.data})

    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
def createPrescrptionItem(request):
    prescription_id = request.query_params.get('prescription_id')  # Get the prescription ID from query params

    # Validate if the patient ID is provided
    if not prescription_id:
        return Response({"status": "error", "message": "Prescription ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Fetch doctor (logged-in user) and patient from the database
        prescription = Patient.objects.get(id=prescription_id)

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

# POST: Create Pre-assessment of Patient
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def createPreassessment(request):
    user_id = request.user.id  # Get the authenticated doctor's ID
    patient_id = request.query_params.get('patient_id')  # Get the patient ID from query params

    print(f"Received POST request for patient_id: {patient_id}")

    if not patient_id:
        print("Error: Missing patient_id")
        return Response({"status": "error", "message": "Patient ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        patient = Patient.objects.get(id=patient_id)
        print(f"Found patient: {patient}")

        # Add doctor and patient to request data
        data = request.data.copy()
        data['doctor'] = user_id
        data['patient'] = patient.id

        print(f"Data to serialize: {data}")

        # Serialize and validate data
        serializer = PreassessmentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            print("Preassessment created successfully!")
            return Response({
                "status": "success",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            print(f"Validation errors: {serializer.errors}")
            return Response({
                "status": "error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    except User.DoesNotExist:
        print("Error: User not found")
        return Response({"status": "error", "message": "Doctor or Patient not found."}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            'id', 'dosage', 'amount', 'drug_name'
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
            patient = prescription.patient
            items = list(prescription.prescriptionitem_set.all())  # Convert QuerySet to list for faster access
        except Prescription.DoesNotExist:
            return Response({"error": "Prescription not found."}, status=status.HTTP_404_NOT_FOUND)

        # ✅ Extract Patient Information
        patient_info = {
            "age": patient.age,
            "weight": f"{patient.weight} kg",
            "medical_conditions": patient.allergies  # Assuming allergies is stored as text
        }

        # ✅ Extract Prescribed Medications List
        prescribed_medications = {
            item.drug_name: {"dosage": item.dosage, "frequency": item.frequency, "amount": item.amount}
            for item in items
        }

        # ✅ Optimize Interaction Query (Avoid Slow `__in` Queries)
        interactions = list(DrugInteractions.objects.filter(
            Q(drug_a__in=prescribed_medications.keys()) | Q(drug_b__in=prescribed_medications.keys())
        ).values("drug_a", "drug_b", "severity", "description", "management"))

        # ✅ Shorten the GPT-4 Prompt to Reduce Token Usage
        prompt = f"""
               You are a medical AI that specializes in analyzing prescriptions. Your task is to:
                - Detect **ALL potential drug-drug interactions**, including **previously detected ones**.
                - Recommend **dosage adjustments** only if necessary, within available market dosages.
                - The reason for dosage adjustments should be **based on effects on the patient** (Do NOT include market availability in 'reason').

               **Patient Info:** Age: {patient_info["age"]}, Weight: {patient_info["weight"]}, Conditions: {patient_info["medical_conditions"]}

               **Medications:** {', '.join([f"{med} ({data['dosage']})" for med, data in prescribed_medications.items()])}

               **Interactions from Database:** {interactions if interactions else "No major interactions detected."}

               **Instructions:**
                - List drug interactions with effects.
                - Suggest dosage changes **only if available in the market**.
                - Return structured **JSON format** strictly.

               **STRICTLY FOLLOW THIS JSON FORMAT:**
               {{
                   "interactions": [{{"drug_a": "", "drug_b": "", "severity": "", "description": "", "management": ""}}],
                   "dosage_adjustments": [{{"drug": "", "current": "", "recommended": "", "reason": ""}}],
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
            cache.set(cache_key, chatbot_reply, timeout=600)  # ✅ Cache the GPT-4 API response
            return Response({"reply": chatbot_reply}, status=status.HTTP_200_OK)
        except Exception as e:
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
            max_tokens=1000  # ✅ Reduce token usage to avoid rate limits
        )
        return response.choices[0].message.content

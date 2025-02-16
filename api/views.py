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
import os
import openai

# Create your views here.

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer #sets the serializer class to the MyTokenObtainPairSerializer we created

class RegisterView(generics.CreateAPIView): #creates a user
    queryset = User.objects.all()
    permission_classes = (AllowAny,) #Allows everyone to access this view
    serializer_class = RegisterSerializer #sets the serializer class to the RegisterSerializer we created

# GET : Fetch the dashboard
@api_view(['GET']) #defining the methods
@permission_classes([IsAuthenticated]) #defining the permission in function based classes
def dashboard(request):

    user_id = request.user.id

    try :
        response = f"Hey {request.user}, Your ID is : {user_id}"
        return Response({'response' : response}, status=status.HTTP_200_OK)
    except:
        return Response({'errorMessage' : 'error in request'}, status=status.HTTP_400_BAD_REQUEST)

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


# POST: Create Prescription of Patient
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def createPrescrption(request):
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

    if not patient_id:
        return Response({"status": "error", "message": "Patient ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        patient = Patient.objects.get(id=patient_id)

        # Add doctor and patient to request data
        data = request.data.copy()
        data['doctor'] = user_id
        data['patient'] = patient.id

        # Serialize and validate data
        serializer = PreassessmentSerializer(data=data)
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
        return Response({"status": "error", "message": "Doctor or Patient not found."}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# DELETE: Remove Pre-assessment of Patient
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def deletePreassessment(request):

    pre_assessmentID = request.query_params.get('pre_assessmentID')  # Get the patient ID from query params

    if not pre_assessmentID:
        return Response({"status": "error", "message": "Pre-assessment ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        pre_assessment = get_object_or_404(PreAssessment, id=pre_assessmentID)
        pre_assessment.remove()
        return Response({"status": "error", "message": "Pre-assessment has been successfully deleted."}, status=status.HTTP_404_NOT_FOUND)

    except User.DoesNotExist:
        return Response({"status": "error", "message": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
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

    prescription_id = request.data.get("prescription_id")
    drug_id = request.data.get("drug_id")

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

        prescription_id = request.query_params.get("prescription_id")

        # Fetch the prescription details
        try:
            prescription = Prescription.objects.get(id=prescription_id) #Gets the prescription container based on ID provided
            patient = Patient.objects.get(id=prescription.patient.id) #Gets the patient based on the patient ID connected to the prescription container
            items = PrescriptionItem.objects.filter(prescription=prescription) #Gets the prescription items under the prescription container

        except Prescription.DoesNotExist:
            return Response({"error": "Prescription not found."}, status=status.HTTP_404_NOT_FOUND)

        patient_info = {
            "age": patient.age,
            "weight": f"{patient.weight} kg",
            "medical_conditions": patient.allergies  #Assuming allergies is stored as a text field
        }

        prescribed_medications = [
            {
                "drug_name": item.drug_name,
                "dosage": item.dosage,
                "frequency": item.frequency
            } for item in items
        ]

        interactions = self.getDrugInteractions(prescribed_medications)

        prompt = f"""
                You are a medical AI specializing in analyzing prescriptions. Your task is to:
                - Detect **ALL the potential drug-drug interactions in the list given** (not just one).
                - Recommend dosage adjustments **where needed**.
                - Provide a final recommendation based on the patient's medical conditions.

                Here is the prescription information:

                Patient Information:
                - Weight: {patient_info["weight"]}
                - Medical Conditions: Allergic to Nitroglycerin

                Prescribed Medications:
                {prescribed_medications}
                
                **Known Drug Interactions (from database):**
                {interactions if interactions else "No major drug interactions detected, review the drugs manually."}

                **Instructions:**
                - List all potential drug interactions and explain their effects.
                - If a drug dosage needs adjustment, provide a recommendation.
                - Summarize safety concerns in a structured JSON output.

                Now, analyze the above information and return a structured JSON output:
                - "potential_drug_interactions": List any potential issues based on known drug interactions.
                - "dosage_adjustment_recommendations": Suggest adjustments if needed.
                - "final_recommendation": A final summary of whether the prescription is safe or if modifications are necessary.
                """


        try:
            # ✅ Fix: Use the new OpenAI SDK format
            client = openai.OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model="chatgpt-4o-latest",  # or "gpt-3.5-turbo"
                messages=[
                    {"role": "system", "content": "You are a medical AI that generates structured prescription analysis reports, strictly follows predefined dosage guidelines. Always return the response in a valid JSON format."},
                    {"role": "user", "content": str(prompt)}
                ],
                temperature=0,
                top_p=1,
                max_tokens=1000

            )
            chatbot_reply = response.choices[0].message.content
            return Response({"reply": chatbot_reply}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def getDrugInteractions(self, prescribed_medications):
        """
        Retrieves potential drug-drug interactions using Django ORM based on the provided list of medications.
        """
        drug_names = [med["drug_name"] for med in prescribed_medications]
        interactions = DrugInteractions.objects.filter(
            drug_a__in=drug_names, drug_b__in=drug_names
        )

        if not interactions.exists():
            return "No major drug interactions detected."

        return [
            {
                "drug_a": interaction.drug_a,
                "drug_b": interaction.drug_b,
                "severity": interaction.severity,
                "description": interaction.description,
                "management": interaction.management,
                "dosage": next((med["dosage"] for med in prescribed_medications if
                                med["drug_name"] in [interaction.drug_a, interaction.drug_b]), None),
                "frequency": next((med["frequency"] for med in prescribed_medications if
                                   med["drug_name"] in [interaction.drug_a, interaction.drug_b]), None),
            } for interaction in interactions
        ]
from django.core.serializers import serialize
from django.shortcuts import render
from rest_framework.generics import get_object_or_404

from api.models import Profile, User, Patient, Prescription, PrescriptionItem
from api.serializers import UserSerializer, MyTokenObtainPairSerializer, RegisterSerializer, PatientSerializer, \
    PrescriptionSerializer, PreassessmentSerializer, ProfileSerializer, PrescriptionItemSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

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

# GET: View Specific Patient
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def getPatientsByID(request, id):

    doctorID = request.user.id

    try:
        # Ensure the doctor exists
        patient = get_object_or_404(Patient, id=id, doctor_id=doctorID) #Filters the patient with only the current logged-in user
        serializer = PatientSerializer(patient)

        if patient.doctor.id == doctorID :
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)
        else :
            return Response({"status" : "error", "message" : "patient and doctor id does not match."}, status=status.HTTP_400_BAD_REQUEST)

    except User.DoesNotExist:
        return Response({"status": "error", "message": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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

# POST: Create Prescription of Patient
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def createPreassessment(request):
    user_id = request.user.id  # Get the authenticated doctor's ID
    patient_id = request.query_params.get('patient_id')  # Get the patient ID from query params

    if not patient_id:
        return Response({"status": "error", "message": "Patient ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Fetch doctor and patient
        doctor = User.objects.get(id=user_id)
        patient = User.objects.get(id=patient_id)

        # Add doctor and patient to request data
        data = request.data.copy()
        data['doctor'] = doctor.id
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

# POST: Create Prescription of Patient
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
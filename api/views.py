from django.core.serializers import serialize
from django.shortcuts import render
from api.models import Profile, User, Patient
from api.serializers import UserSerializer, MyTokenObtainPairSerializer, RegisterSerializer, PatientSerializer
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

@api_view(['GET', 'POST']) #defining the methods
@permission_classes([IsAuthenticated]) #defining the permission in function based classes
def dashboard(request):

    user_ID = request.user.id

    if request.method == "GET":

        response = f"Hey {request.user}, This is the GET response with authentication. Your ID is {user_ID}"
        return Response({'response' : response}, status=status.HTTP_200_OK)

    elif request.method == "POST" :

        text = request.POST.get("text") #Gets the request with text (parang req.body.text in node.js)
        text = f"Hey, {request.user}, your text is { text }"
        return Response({'response' : text}, status=status.HTTP_200_OK)

    return Response({'errorMessage' : 'Error in request'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def createPatient(request):

    if request.method == 'POST':

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
    elif request.method == 'GET':
        doctor_id = request.query_params.get('doctor_id')  # Use query params for filtering
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


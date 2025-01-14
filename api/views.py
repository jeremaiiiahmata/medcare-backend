from django.shortcuts import render
from api.models import Profile, User
from api.serializers import UserSerializer, MyTokenObtainPairSerializer, RegisterSerializer
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

    if request.method == "GET":

        response = f"Hey {request.user}, This is the GET response with authentication"
        return Response({'response' : response}, status=status.HTTP_200_OK)

    elif request.method == "POST" :

        text = request.POST.get("text") #Gets the request with text (parang req.body.text in node.js)
        text = f"Hey, {request.user}, your text is { text }"
        return Response({'response' : text}, status=status.HTTP_200_OK)

    return Response({'errorMessage' : 'Error in request'}, status=status.HTTP_400_BAD_REQUEST)
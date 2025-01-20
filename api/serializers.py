from rest_framework_simplejwt.tokens import Token
from setuptools.config.pyprojecttoml import validate

from api.models import User, Profile, Patient, Prescription, PreAssessment, PrescriptionItem
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, AuthUser
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token['first_name'] = user.profile.first_name
        token['username'] = user.username
        token['middle_name'] = user.profile.middle_name
        token['last_name'] = user.profile.last_name
        token['specialization'] = user.profile.specialization
        token['contact_number'] = user.profile.contact_number
        token['office_address'] = user.profile.office_address
        token['bio'] = user.profile.bio
        token['image'] = str(user.profile.image) #convert this to string so it can be serializer

        return token

class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField (
        write_only=True, required=True, validators=[validate_password]
    )
    passwordValidator = serializers.CharField( #Confirm Password
        write_only=True, required=True)

    class Meta :
        model = User
        fields = ['email', 'username', 'password', 'passwordValidator']

    def validate(self, attrs): #Function that validates the password, attrs is from the fields up in the meta class

        if attrs['password'] != attrs['passwordValidator'] : # If we have all the fields up in the meta class
            raise serializers.ValidationError(
                {"password" : "Password fields does not match."}
            )

        return attrs

    def create(self, validated_data): #same as the attrs, these are the fields up in the meta class
        user = User.objects.create(
            username = validated_data['username'],
            email = validated_data['email'],
        )

        user.set_password(validated_data['password']) #set_password hashes the password
        user.save() #Saves the user

        return user

class ProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = Profile
        fields = ['id', 'first_name', 'middle_name', 'last_name', 'specialization', 'contact_number', 'office_address', 'bio', 'image']

class PatientSerializer(serializers.ModelSerializer): #Serializer for Patient, eto yung mga nasa JSON. MUST MATCH DIN SA POST IN REACT

    class Meta :
        model = Patient
        fields = ['id', 'doctor', 'first_name', 'last_name', 'blood_type', 'email', 'contact_number',
                  'address', 'age', 'weight', 'gender', 'id_number', 'allergies']

class PrescriptionSerializer(serializers.ModelSerializer): #Serializer for Patient, eto yung mga nasa JSON. MUST MATCH DIN SA POST IN REACT

    class Meta :
        model = Prescription
        fields = ['title', 'description', 'doctor', 'patient', 'date_created']

class PrescriptionItemSerializer(serializers.ModelSerializer): #Serializer for Patient, eto yung mga nasa JSON. MUST MATCH DIN SA POST IN REACT

    class Meta :
        model = PrescriptionItem
        fields = ['prescription', 'amount', 'drug_name', 'dosage', 'frequency', 'notes']

class PreassessmentSerializer(serializers.ModelSerializer): #Serializer for Patient, eto yung mga nasa JSON. MUST MATCH DIN SA POST IN REACT

    class Meta :
        model = PreAssessment
        fields = ['doctor', 'patient', 'date_created', 'heart_rate', 'temperature', 'complaint', 'notes', 'recommendations', 'symptoms']
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

class PrescriptionItemSerializer(serializers.ModelSerializer): #Serializer for Patient, eto yung mga nasa JSON. MUST MATCH DIN SA POST IN REACT


    class Meta :
        model = PrescriptionItem
        fields = ['id', 'prescription', 'amount', 'drug_name', 'dosage', 'frequency', 'notes']

class PreassessmentSerializer(serializers.ModelSerializer): #Serializer for Patient, eto yung mga nasa JSON. MUST MATCH DIN SA POST IN REACT
    patient = PatientSerializer(read_only=True)

    class Meta :
        model = PreAssessment
        fields = '__all__'

class PrescriptionSerializer(
    serializers.ModelSerializer):  # Serializer for Patient, eto yung mga nasa JSON. MUST MATCH DIN SA POST IN REACT
    preassessment = PreassessmentSerializer(read_only=True)
    patient = PatientSerializer(read_only=True)

    class Meta:
        model = Prescription
        fields = ['id', 'doctor', 'patient', 'title', 'description', 'date_created', 'preassessment']

class ChatbotSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, max_length=500)

class DashboardSerializer(serializers.Serializer):
    total_doctors = serializers.IntegerField()
    total_patients = serializers.IntegerField()
    total_prescriptions = serializers.IntegerField()
    total_pre_assessments = serializers.IntegerField()
    total_drug_interactions = serializers.IntegerField()
    patients_per_doctor = serializers.DictField(child=serializers.IntegerField())
    most_prescribed_drugs = serializers.ListField(child=serializers.DictField())
    recent_prescriptions = serializers.ListField(child=serializers.DictField())
    flagged_interactions = serializers.IntegerField()
    recent_pre_assessments = serializers.ListField(child=serializers.DictField())
    age_distribution = serializers.DictField(child=serializers.IntegerField())
    active_patients = serializers.IntegerField()
    inactive_patients = serializers.IntegerField()
    doctor_workload = serializers.ListField(child=serializers.DictField())
    common_drug_interactions = serializers.ListField(child=serializers.DictField())
    chronic_conditions_count = serializers.IntegerField()
    most_common_symptoms = serializers.ListField(child=serializers.DictField())
    average_patient_age = serializers.FloatField()
    monthly_prescription_trend = serializers.ListField(child=serializers.DictField())
    top_diagnosed_conditions = serializers.ListField(child=serializers.DictField())
    prescription_completion_rate = serializers.FloatField()


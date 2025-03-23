from django.core.mail import send_mail
from django.conf import settings

def send_otp_email(user):
    user.generate_otp()  # Generate OTP and save to database
    subject = "MedCare Login - OTP Code"
    message = f"Your OTP code is: {user.otp}. It will expire in 5 minutes."
    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])
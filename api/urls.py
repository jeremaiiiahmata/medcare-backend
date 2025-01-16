from rest_framework_simplejwt.views import TokenRefreshView
from django.urls import path
from . import views

urlpatterns = [
    path('token', views.MyTokenObtainPairView.as_view()), #use .as_view() for class based views
    path('token/refresh', TokenRefreshView.as_view()),
    path('register', views.RegisterView.as_view()),
    path('dashboard', views.dashboard), #function-based views
    path('create-patient', views.createPatient),
]
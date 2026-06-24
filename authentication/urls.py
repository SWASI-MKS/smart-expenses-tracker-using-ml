from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from .views import GoodbyeView
from .views import VerifyOTPView
from .views import (
    RegistrationView,
    UsernameValidationView,
    EmailValidationView,
    LoginView,
    VerificationView,
    LogoutView,
    LandingPageView
)

urlpatterns = [
    path('', LandingPageView.as_view(), name='home'),
    path('register/', RegistrationView.as_view(), name='register'),

    path(
        'validate-username/',
        csrf_exempt(UsernameValidationView.as_view()),
        name='validate-username'
    ),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),

    path(
        'validate-email/',
        csrf_exempt(EmailValidationView.as_view()),
        name='validate-email'
    ),

    path('login/', LoginView.as_view(), name='login'),
    path('activate/<uidb64>/<token>/', VerificationView.as_view(), name='activate'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('goodbye/', GoodbyeView.as_view(), name='goodbye'),
]

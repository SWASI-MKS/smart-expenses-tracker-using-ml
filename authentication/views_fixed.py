from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.models import User
import json
from django.http import JsonResponse
from validate_email import validate_email
from django.contrib import messages
from django.core.mail import EmailMessage
from django.utils.encoding import force_bytes, force_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from .utils import account_activation_token
from django.db import transaction
from django.contrib import auth
from django.contrib.auth.decorators import login_required
import random
from django.core.mail import send_mail
from django.conf import settings


class EmailValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data['email']
        if not validate_email(email):
            return JsonResponse({'emailerror': 'Email is invalid'}, status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({'emailerror': 'sorry email in use, choose another one'}, status=409)
        return JsonResponse({'email_valid': True})


class UsernameValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        username = data['username']
        if not str(username).isalnum():
            return JsonResponse({'usernameerror': 'username should only contain alphanumeric characters'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'usernameerror': 'sorry username in use, choose another one'}, status=409)
        return JsonResponse({'username_valid': True})


class RegistrationView(View):
    def get(self, request):
        return render(request, 'authentication/register.html')

    def post(self, request):
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        context = {'fieldValues': request.POST}

        if not username or not email or not password:
            messages.error(request, "Please fill all fields")
            return render(request, 'authentication/register.html', context)

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return render(request, 'authentication/register.html', context)

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return render(request, 'authentication/register.html', context)

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters")
            return render(request, 'authentication/register.html', context)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        user.is_active = False
        user.save()

        otp = random.randint(100000, 999999)
        request.session['otp'] = otp
        request.session['user_id'] = user.id

        send_mail(
            'Your OTP Verification Code',
            f'Your OTP is {otp}',
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        return redirect('verify-otp')


class LoginView(View):
    def get(self, request):
        return render(request, 'authentication/login.html')

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']
        if username and password:
            user = None
            if '@' in username:
                try:
                    user_obj = User.objects.get(email=username)
                    user = auth.authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            else:
                user = auth.authenticate(username=username, password=password)
            if user:
                if user.is_active:
                    auth.login(request, user)
                    messages.success(request, "Welcome, " +
                                     user.username + " you are now logged in")
                    return redirect('overview')
                messages.error(
                    request, 'Account is not active, Please check your email')
                return render(request, 'authentication/login.html')
            messages.error(request, "Invalid credentials, try again")
            return render(request, "authentication/login.html")
        messages.error(request, "Please fill all fields")
        return render(request, "authentication/login.html")


class VerificationView(View):
    def get(self, request, uidb64, token):
        try:
            id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=id)

            if not account_activation_token.check_token(user, token):
                return redirect('login'+'?message='+'User already activated')

            if user.is_active:
                return redirect('login')
            user.is_active = True
            user.save()
            messages.success(request, 'Account activated Successfully')
            return redirect('login')
        except Exception as e:
            pass
        return redirect('login')


class LogoutView(View):
    def get(self, request):
        return render(request, 'authentication/logout.html')

    def post(self, request):
        auth.logout(request)
        messages.success(request, "You have been logged out successfully")
        return redirect('home')


class GoodbyeView(View):
    def get(self, request):
        return render(request, 'authentication/goodbye.html')


class LandingPageView(View):
    def get(self, request):
        # Show landing page to everyone - logged in users can access dashboard via link
        return render(request, 'authentication/homepage.html')


class VerifyOTPView(View):
    def get(self, request):
        return render(request, 'authentication/verify_otp.html')

    def post(self, request):
        entered_otp = request.POST.get('otp')
        session_otp = request.session.get('otp')
        user_id = request.session.get('user_id')

        if str(entered_otp) == str(session_otp):
            user = User.objects.get(id=user_id)
            user.is_active = True
            user.save()

            auth.login(request, user)

            request.session.pop('otp', None)
            request.session.pop('user_id', None)

            return redirect('overview')

        messages.error(request, "Invalid OTP")
        return render(request, 'authentication/verify_otp.html')

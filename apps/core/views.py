from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from apps.core.models import Learner, Developer

def login_view(request):
    if request.user.is_authenticated:
        return redirect('learner:dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, "Please enter both username and password.")
            return render(request, 'core/login.html')
            
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            # Redirect based on user profile type
            if hasattr(user, 'developer_profile'):
                return redirect('developer:portal')
            return redirect('learner:dashboard')
        else:
            messages.error(request, "Invalid username or password.")
            
    return render(request, 'core/login.html')

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('learner:dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        role = request.POST.get('role', 'learner')  # learner or developer
        
        if not username or not email or not password:
            messages.error(request, "All fields are required.")
            return render(request, 'core/signup.html')
            
        if password != password_confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, 'core/signup.html')
            
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'core/signup.html')
            
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return render(request, 'core/signup.html')
            
        # Create user
        user = User.objects.create_user(username=username, email=email, password=password)
        
        # Create profile based on selected role
        if role == 'developer':
            Developer.objects.create(user=user)
            messages.success(request, "Developer account created! Welcome to ExcellStudy.")
            login(request, user)
            return redirect('developer:portal')
        else:
            Learner.objects.create(user=user)
            messages.success(request, "Account created successfully! Welcome to ExcellStudy.")
            login(request, user)
            return redirect('learner:dashboard')
            
    return render(request, 'core/signup.html')

def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('home')

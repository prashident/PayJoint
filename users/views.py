# users/views.py
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User # Need User model
from django.contrib import messages
from django.db import transaction

# Import forms from this app
from .forms import LoginForm, SignupForm, EditProfileForm

# Supabase client (assuming it's used globally and needs to be accessible in all relevant views)
from supabase import create_client, Client
supabase_url = os.environ.get("SUPABASE_URL", "https://tnbfyzliuicmstdkmlej.supabase.co")
supabase_key = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRuYmZ5emxpdWljbXN0ZGttbGVqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzI4ODM4MywiZXhwIjoyMDY4ODY0MzgzfQ.vAgT5fKkRtR8CBPP-eCy7pJNFDQiidYiS_etrDcDUO8")
supabase: Client = create_client(supabase_url, supabase_key)


def index_view(request):
    if request.user.is_authenticated:
        return redirect('groups:dashboard') # Redirect logged-in users to their dashboard
    return render(request, 'users/index.html') # Render the index.html from the users app template directory

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            try:
                with transaction.atomic():
                    user = User.objects.create_user(username=username, email=email, password=password)
                    user.is_active = True
                    user.save()

                    supabase_user_data = {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "created_at": user.date_joined.isoformat(),
                    }
                    user_response = supabase.table("users").insert(supabase_user_data).execute()

                    if not user_response.data:
                        messages.error(request, f"Failed to sync user with Supabase 'users' table: {user_response.error.message}")
                        raise Exception("Supabase 'users' sync failed")

                    supabase_profile_data = {
                        "id": user.id,
                        "email": user.email,
                        "username": user.username,
                        "created_at": user.date_joined.isoformat(),
                    }
                    profile_response = supabase.table("profiles").insert(supabase_profile_data).execute()

                    if not profile_response.data:
                        messages.error(request, f"Failed to sync user profile with Supabase 'profiles' table: {profile_response.error.message}")
                        raise Exception("Supabase 'profiles' sync failed")

                    login(request, user)
                    messages.success(request, "Account created successfully! Welcome to PayJoint.")
                    return redirect('groups:dashboard')

            except Exception as e:
                messages.error(request, f"An error occurred during signup: {e}")
                return render(request, 'users/auth.html', {'form': form, 'is_signup': True})

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, error)
    else:
        form = SignupForm()
    return render(request, 'users/auth.html', {'form': form, 'is_signup': True})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('groups:dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = None
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                messages.error(request, "Invalid email or password.")
                return render(request, 'users/auth.html', {'form': form, 'is_signup': False})

            if user.check_password(password):
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('groups:dashboard')
            else:
                messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()
    return render(request, 'users/auth.html', {'form': form, 'is_signup': False})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect('users:login') # Changed redirect name to new app's url

@login_required
def profile_detail_view(request):
    return render(request, 'users/profile_detail.html', {'user': request.user})

@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('users:profile_detail') # Changed redirect name
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, error)
    else:
        form = EditProfileForm(instance=request.user)
    return render(request, 'edit_profile_page.html', {'form': form})
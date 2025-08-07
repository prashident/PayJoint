# users/views.py
import os
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from supabase import create_client, Client

# Supabase client configuration
supabase_url = os.environ.get("SUPABASE_URL", "https://tnbfyzliuicmstdkmlej.supabase.co")
supabase_key = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRuYmZ5emxpdWljbXN0ZGttbGVqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzI4ODM4MywiZXhwIjoyMDY4ODY0MzgzfQ.vAgT5fKkRtR8CBPP-eCy7pJNFDQiidYiS_etrDcDUO8")
supabase: Client = create_client(supabase_url, supabase_key)


def index_view(request):
    """
    Renders the index page.
    Redirects authenticated users to their groups dashboard.
    """
    if request.user.is_authenticated:
        return redirect('groups:dashboard')
    return render(request, 'users/index.html')


# The following custom authentication views have been removed.
# Django-Allauth now handles signup, login, and logout.
# You no longer need:
# - signup_view
# - login_view
# - logout_view


@login_required
def profile_detail_view(request):
    """
    Displays the profile of the currently logged-in user.
    """
    return render(request, 'users/profile_detail.html', {'user': request.user})


@login_required
def edit_profile_view(request):
    """
    Handles editing the user's profile.
    """
    from .forms import EditProfileForm
    from django.contrib import messages
    
    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('users:profile_detail')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = EditProfileForm(instance=request.user)
    return render(request, 'edit_profile_page.html', {'form': form})
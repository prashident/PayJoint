import os
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings
from supabase import create_client, Client

# Supabase client configuration
supabase_url = settings.SUPABASE_URL
supabase_key = settings.SUPABASE_KEY

# Initialize the client
supabase: Client = create_client(supabase_url, supabase_key)

def index_view(request):
    if request.user.is_authenticated:
        return redirect('groups:dashboard')
    return render(request, 'users/index.html')

@login_required
def profile_detail_view(request):
    """
    Displays the one-page profile.
    """
    return render(request, 'users/profile_detail.html', {'user': request.user})

@login_required
@require_POST
def update_profile(request):
    """
    AJAX endpoint to update first_name and last_name.
    Syncs with local Django User and Supabase 'users' + 'profiles' tables.
    """
    try:
        data = json.loads(request.body)
        user = request.user
        
        # 1. Update Django Local Database
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.save()

        # 2. Update Supabase 'users' table
        # Matches your schema: {id: int8, first_name: text, last_name: text...}
        supabase_data = {
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
        
        # Syncing both tables as per your schema image
        supabase.table("users").update(supabase_data).eq("id", user.id).execute()
        supabase.table("profiles").update(supabase_data).eq("id", user.id).execute()

        return JsonResponse({
            "status": "success", 
            "message": "Profile updated successfully!",
            "full_name": f"{user.first_name} {user.last_name}".strip() or user.username
        })
    
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
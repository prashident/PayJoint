from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
import os
from supabase import create_client, Client

# Supabase client
supabase_url = os.environ.get("SUPABASE_URL", "https://tnbfyzliuicmstdkmlej.supabase.co")
supabase_key = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRuYmZ5emxpdWljbXN0ZGttbGVqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzI4ODM4MywiZXhwIjoyMDY4ODY0MzgzfQ.vAgT5fKkRtR8CBPP-eCy7pJNFDQiidYiS_etrDcDUO8")
supabase: Client = create_client(supabase_url, supabase_key)


@receiver(post_save, sender=User)
def create_supabase_user(sender, instance, created, **kwargs):
    """
    Creates a new user record in Supabase when a new user is created in Django.
    """
    if created:
        try:
            # We use the Django user ID as the ID for the Supabase record
            supabase_data = {
                "id": str(instance.id),
                "email": instance.email,
                "username": instance.username,
                # Add any other fields you need to sync
            }
            # This inserts a new record into your 'users' table in Supabase
            response = supabase.table("users").insert(supabase_data).execute()
            print(f"Supabase user created: {response.data}")

        except Exception as e:
            print(f"Failed to sync user with Supabase: {e}")
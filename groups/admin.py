from django.contrib import admin
from .models import Group, Invitation

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    # This adds the code to the main table view
    list_display = ('name', 'invite_code', 'group_type', 'created_by', 'created_at')
    
    # This ensures it shows up inside the group details page
    # Since it's non-editable in the model, it MUST be in readonly_fields
    readonly_fields = ('invite_code', 'created_at')
    
    # Adds a search bar to find groups by name or their 6-digit code
    search_fields = ('name', 'invite_code')
    
    # Adds a filter sidebar for quick sorting
    list_filter = ('group_type', 'created_at')

@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('invited_email', 'group', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('invited_email', 'group__name')
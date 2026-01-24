# expenses/views.py
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# Import Group model from the groups app
from groups.models import Group
# Import Expense model and ExpenseForm from this app
from .models import Expense
from .forms import ExpenseForm

# Supabase client (assuming it's used globally and needs to be accessible in all relevant views)
from supabase import create_client, Client
supabase_url = os.environ.get("SUPABASE_URL", "https://tnbfyzliuicmstdkmlej.supabase.co")
supabase_key = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRuYmZ5emxpdWljbXN0ZGttbGVqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzI4ODM4MywiZXhwIjoyMDY4ODY0MzgzfQ.vAgT5fKkRtR8CBPP-eCy7pJNFDQiidYiS_etrDcDUO8")
supabase: Client = create_client(supabase_url, supabase_key)


@login_required
def add_expense_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    # Security check
    if request.user not in group.members.all():
        messages.error(request, "Access denied.")
        return redirect('groups:dashboard')

    if request.method == 'POST':
        # 1. Capture the data from the modal
        form = ExpenseForm(request.POST)
        
        # 2. Re-bind querysets to the specific group
        form.fields['participants'].queryset = group.members.all()
        form.fields['paid_by'].queryset = group.members.all()

        if form.is_valid():
            expense = form.save(commit=False)
            expense.group = group
            # If your modal doesn't have a 'paid_by' selector, default to current user
            expense.paid_by = form.cleaned_data.get('paid_by') or request.user
            expense.save()
            
            # Use 'set()' for ManyToMany fields
            # If modal doesn't specify participants, default to all members
            participants = form.cleaned_data.get('participants') or group.members.all()
            expense.participants.set(participants)
            
            messages.success(request, "Expense added successfully!")
        else:
            # If form is invalid, send errors to messages so they show up on the Group Detail page
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    
    # ALWAYS redirect back to the Detail page, never render a separate page
    return redirect('groups:group_detail', group_id=group.id)

@login_required
def delete_expense(request, expense_id):
    if request.method == 'POST':
        expense = get_object_or_404(Expense, id=expense_id)
        group_id = expense.group.id
        
        # Security: Only allow the person who paid or the group creator to delete
        if request.user == expense.paid_by or request.user == expense.group.created_by:
            expense.delete()
            messages.success(request, "Expense deleted successfully.")
        else:
            messages.error(request, "You don't have permission to delete this expense.")
            
        return redirect('groups:group_detail', group_id=group_id)
    
    return redirect('groups:dashboard')


@login_required
def settle_expense_part(request, expense_id):
    if request.method == 'POST':
        expense = get_object_or_404(Expense, id=expense_id)
        
        # Check if user is actually part of this expense
        if request.user in expense.participants.all():
            if request.user in expense.settled_by.all():
                expense.settled_by.remove(request.user) # Unsettle
                messages.info(request, "Marked as unsettled.")
            else:
                expense.settled_by.add(request.user) # Settle
                messages.success(request, "Your share is marked as paid!")
        
        return redirect('groups:group_detail', group_id=expense.group.id)
    return redirect('groups:dashboard')


@login_required
def add_dashboard_expense(request):
    if request.method == 'POST':
        group_id = request.POST.get('group')
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        category = request.POST.get('category', 'Misc')

        # 1. Get the group and verify the user belongs to it
        group = get_object_or_404(Group, id=group_id)
        if request.user not in group.members.all():
            messages.error(request, "You aren't a member of that group!")
            return redirect('groups:dashboard')

        # 2. Create the expense
        expense = Expense.objects.create(
            group=group,
            paid_by=request.user,
            amount=amount,
            description=description,
            category=category
        )

        # 3. Default Split: Automatically include all group members
        expense.participants.set(group.members.all())
        expense.save()

        messages.success(request, f"₹{amount} added to {group.name} successfully!")
        return redirect('groups:dashboard')
    
    return redirect('groups:dashboard')
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

    if request.user not in group.members.all():
        messages.error(request, "You cannot add expenses to a group you are not a member of.")
        return redirect('groups:dashboard') # Changed redirect name

    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        form.fields['participants'].queryset = group.members.all()
        form.fields['paid_by'].queryset = group.members.all()

        if form.is_valid():
            expense = form.save(commit=False)
            expense.group = group
            expense.paid_by = form.cleaned_data['paid_by']
            expense.save()
            expense.participants.set(form.cleaned_data['participants'])
            messages.success(request, "Expense added successfully!")
            return redirect('groups:group_detail', group_id=group.id) # Changed redirect name
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = ExpenseForm()
        form.fields['participants'].queryset = group.members.all()
        form.fields['paid_by'].queryset = group.members.all()
        form.initial['paid_by'] = request.user
        form.initial['participants'] = group.members.all()

    context = {
        'form': form,
        'group': group,
    }
    return render(request, 'expenses/add_expense_modal.html', context)
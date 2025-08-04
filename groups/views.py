# groups/views.py
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal

# Import User from django.contrib.auth.models
from django.contrib.auth.models import User

# Import models and forms from this app
from .models import Group, Invitation
from .forms import GroupForm, InvitationForm

# Import Expense model from the expenses app
from expenses.models import Expense

# Supabase client (assuming it's used globally and needs to be accessible in all relevant views)
from supabase import create_client, Client
supabase_url = os.environ.get("SUPABASE_URL", "https://tnbfyzliuicmstdkmlej.supabase.co")
supabase_key = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRuYmZ5emxpdWljbXN0ZGttbGVqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzI4ODM4MywiZXhwIjoyMDY4ODY0MzgzfQ.vAgT5fKkRtR8CBPP-eCy7pJNFDQiidYiS_etrDcDUO8")
supabase: Client = create_client(supabase_url, supabase_key)


@login_required
def dashboard_view(request):
    user_groups = request.user.joined_groups.all()

    total_owed_to_user = Decimal('0.00')
    total_user_owes = Decimal('0.00')

    groups_with_details = []

    for group in user_groups:
        # Now importing Expense from expenses.models explicitly
        expenses = Expense.objects.filter(group=group) # Use Expense model from its app
        members = group.members.all()

        balances_in_group = {member.id: Decimal(0) for member in members}
        for expense in expenses:
            payer_id = expense.paid_by.id
            amount = expense.amount

            balances_in_group[payer_id] += amount

            if expense.participants.exists():
                share = amount / Decimal(expense.participants.count())
                for participant in expense.participants.all():
                    balances_in_group[participant.id] -= share
        
        user_balance_in_this_group = balances_in_group.get(request.user.id, Decimal(0))
        
        if user_balance_in_this_group > 0:
            total_owed_to_user += user_balance_in_this_group
        elif user_balance_in_this_group < 0:
            total_user_owes += abs(user_balance_in_this_group)

        group_total_expenses = group.get_total_expenses_amount()
        budget_limit = None

        if group.budget is not None and group.budget > 0:
            budget_limit = group.budget
        elif group.group_type == 'Trip' and group.individual_budget is not None and group.individual_budget > 0:
            budget_limit = group.individual_budget * Decimal(group.members.count())
        elif group.group_type == 'Home' and group.monthly_home_budget is not None and group.monthly_home_budget > 0:
            budget_limit = group.monthly_home_budget

        budget_percentage_spent = 0
        if budget_limit is not None and budget_limit > 0:
            budget_percentage_spent = (group_total_expenses / budget_limit) * 100
            if budget_percentage_spent > 100:
                budget_percentage_spent = 100

        remaining_budget_amount = None
        if budget_limit is not None:
            remaining_budget_amount = budget_limit - group_total_expenses

        groups_with_details.append({
            'group': group,
            'user_balance': user_balance_in_this_group.quantize(Decimal('0.01')),
            'total_expenses_amount': group_total_expenses.quantize(Decimal('0.01')),
            'budget_limit': budget_limit.quantize(Decimal('0.01')) if budget_limit is not None else None,
            'budget_percentage_spent': round(budget_percentage_spent, 2),
            'remaining_budget_amount': remaining_budget_amount.quantize(Decimal('0.01')) if remaining_budget_amount is not None else None,
        })


    context = {
        'user_groups': user_groups,
        'groups_with_details': groups_with_details,
        'current_user_id': request.user.id,
        'total_owed_to_user': total_owed_to_user.quantize(Decimal('0.01')),
        'total_user_owes': total_user_owes.quantize(Decimal('0.01')),
    }
    return render(request, 'groups/dashboard.html', context)

@login_required
def create_group_view(request):
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                group = form.save(commit=False)
                group.created_by = request.user

                group_type = form.cleaned_data.get('group_type')
                if group_type == 'Trip':
                    group.start_date = form.cleaned_data.get('start_date')
                    group.end_date = form.cleaned_data.get('end_date')
                    group.individual_budget = form.cleaned_data.get('individual_budget')
                    group.monthly_home_budget = None
                elif group_type == 'Home':
                    group.monthly_home_budget = form.cleaned_data.get('monthly_home_budget')
                    group.start_date = None
                    group.end_date = None
                    group.individual_budget = None
                else:
                    group.start_date = None
                    group.end_date = None
                    group.individual_budget = None
                    group.monthly_home_budget = None

                group.save()

                if group.image:
                    image_file = group.image
                    file_extension = os.path.splitext(image_file.name)[1]
                    image_path_in_storage = f"group_images/{group.id}{file_extension}"

                    try:
                        image_content = image_file.read()
                        storage_res = supabase.storage.from_("group_images_bucket").upload(
                            image_path_in_storage,
                            image_content,
                            file_options={"content-type": image_file.content_type}
                        )

                        if storage_res.status_code == 200:
                            public_url = supabase.storage.from_("group_images_bucket").get_public_url(image_path_in_storage)
                            group.image.name = public_url
                            group.save(update_fields=['image'])
                        else:
                            messages.warning(request, f"Failed to upload group image to Supabase Storage: {storage_res.json()}")
                    except Exception as e:
                        messages.warning(request, f"Error processing group image upload to Supabase: {e}")

                group.members.add(request.user)

                member_ids_for_supabase = [str(request.user.id)]
                supabase_data = {
                    "id": str(group.id),
                    "name": group.name,
                    "description": group.description,
                    "created_by_id": str(group.created_by.id),
                    "created_by_email": group.created_by.email,
                    "member_ids": member_ids_for_supabase,
                    "created_at": group.created_at.isoformat(),
                    "image_url": group.image.name if group.image else None,
                    "budget": float(group.budget) if group.budget is not None else None,
                    "group_type": group.group_type,
                    "start_date": group.start_date.isoformat() if group.start_date else None,
                    "end_date": group.end_date.isoformat() if group.end_date else None,
                    "individual_budget": float(group.individual_budget) if group.individual_budget is not None else None,
                    "monthly_home_budget": float(group.monthly_home_budget) if group.monthly_home_budget is not None else None,
                }
                try:
                    response = supabase.table("groups").insert(supabase_data).execute()

                    if response.data:
                        messages.success(request, f"Group '{group.name}' created and synced with Supabase successfully!")
                    else:
                        messages.warning(request, f"Group '{group.name}' created, but failed to sync with Supabase. Error: {response.error.message}")
                        raise Exception("Supabase sync failed")
                except Exception as e:
                    messages.error(request, f"An error occurred while syncing with Supabase: {e}")
                    raise

            return redirect('groups:dashboard') # Changed redirect name
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, error)
    else:
        form = GroupForm()
    return render(request, 'groups/create_group_modal.html', {'form': form})

@login_required
def edit_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if group.created_by != request.user:
        messages.error(request, "You do not have permission to edit this group.")
        return redirect('groups:group_detail', group_id=group.id) # Changed redirect name

    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES, instance=group)
        if form.is_valid():
            with transaction.atomic():
                group = form.save(commit=False)

                group_type = form.cleaned_data.get('group_type')
                if group_type == 'Trip':
                    group.start_date = form.cleaned_data.get('start_date')
                    group.end_date = form.cleaned_data.get('end_date')
                    group.individual_budget = form.cleaned_data.get('individual_budget')
                    group.monthly_home_budget = None
                elif group_type == 'Home':
                    group.monthly_home_budget = form.cleaned_data.get('monthly_home_budget')
                    group.start_date = None
                    group.end_date = None
                    group.individual_budget = None
                else:
                    group.start_date = None
                    group.end_date = None
                    group.individual_budget = None
                    group.monthly_home_budget = None

                if 'image' in request.FILES:
                    image_file = request.FILES['image']
                    file_extension = os.path.splitext(image_file.name)[1]
                    image_path_in_storage = f"group_images/{group.id}{file_extension}"
                    try:
                        image_content = image_file.read()
                        storage_res = supabase.storage.from_("group_images_bucket").upload(
                            image_path_in_storage, image_content, file_options={"content-type": image_file.content_type, "upsert": True}
                        )
                        if storage_res.status_code == 200:
                            public_url = supabase.storage.from_("group_images_bucket").get_public_url(image_path_in_storage)
                            group.image.name = public_url
                        else:
                            messages.warning(request, f"Failed to upload new group image to Supabase Storage: {storage_res.json()}")
                    except Exception as e:
                        messages.warning(request, f"Error processing new group image upload to Supabase: {e}")
                elif form.cleaned_data.get('image-clear'):
                    if group.image and "group_images/" in group.image.name:
                        try:
                            path_to_delete = group.image.name.split("group_images_bucket/")[1]
                            supabase.storage.from_("group_images_bucket").remove([path_to_delete])
                        except Exception as e:
                            messages.warning(request, f"Failed to delete old image from Supabase Storage: {e}")
                    group.image = None

                group.save()

                supabase_update_data = {
                    "name": group.name,
                    "description": group.description,
                    "image_url": group.image.name if group.image else None,
                    "budget": float(group.budget) if group.budget is not None else None,
                    "group_type": group.group_type,
                    "start_date": group.start_date.isoformat() if group.start_date else None,
                    "end_date": group.end_date.isoformat() if group.end_date else None,
                    "individual_budget": float(group.individual_budget) if group.individual_budget is not None else None,
                    "monthly_home_budget": float(group.monthly_home_budget) if group.monthly_home_budget is not None else None,
                }

                try:
                    response = supabase.table("groups").update(supabase_update_data).eq("id", str(group.id)).execute()

                    if response.data:
                        messages.success(request, f"Group '{group.name}' updated and synced with Supabase successfully!")
                    else:
                        messages.warning(request, f"Group '{group.name}' updated, but failed to sync with Supabase. Error: {response.error.message}")
                        raise Exception("Supabase update failed")
                except Exception as e:
                    messages.error(request, f"An error occurred while syncing updates with Supabase: {e}")
                    raise

            return redirect('groups:group_detail', group_id=group.id) # Changed redirect name
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, error)
    else:
        form = GroupForm(instance=group)
        if group.individual_budget is not None:
            form.initial['set_individual_budget'] = True

    return render(request, 'create_group_modal.html', {'form': form})

@login_required
def group_detail_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if request.user not in group.members.all():
        messages.error(request, "You are not a member of this group.")
        return redirect('groups:dashboard') # Changed redirect name

    # Now importing Expense from expenses.models explicitly
    expenses = Expense.objects.filter(group=group) # Use Expense model from its app
    members = group.members.all()

    total_spent = group.get_total_expenses_amount()
    remaining_budget = group.get_remaining_budget()

    balances = {member.id: Decimal(0) for member in members}
    for expense in expenses:
        payer_id = expense.paid_by.id
        amount = expense.amount

        balances[payer_id] += amount

        if expense.participants.exists():
            share = amount / Decimal(expense.participants.count())
            for participant in expense.participants.all():
                balances[participant.id] -= share

    formatted_balances = []
    for member in members:
        balance = balances.get(member.id, Decimal(0))
        if balance != Decimal(0):
            formatted_balances.append({
                'user': member,
                'balance': balance
            })

    settlements = []
    positive_balances = sorted([b for b in formatted_balances if b['balance'] > Decimal(0)], key=lambda x: x['balance'], reverse=True)
    negative_balances = sorted([b for b in formatted_balances if b['balance'] < Decimal(0)], key=lambda x: x['balance'])

    i, j = 0, 0
    while i < len(negative_balances) and j < len(positive_balances):
        debtor = negative_balances[i]
        creditor = positive_balances[j]

        amount_to_settle = min(abs(debtor['balance']), creditor['balance'])

        settlements.append({
            'from_user': debtor['user'],
            'to_user': creditor['user'],
            'amount': amount_to_settle
        })

        debtor['balance'] += amount_to_settle
        creditor['balance'] -= amount_to_settle

        if round(debtor['balance'], 2) == Decimal(0):
            i += 1
        if round(creditor['balance'], 2) == Decimal(0):
            j += 1
    
    current_user_balance_val = balances.get(request.user.id, Decimal(0))
    current_user_balance = current_user_balance_val.quantize(Decimal('0.01'))

    context = {
        'group': group,
        'expenses': expenses,
        'members': members,
        'formatted_balances': formatted_balances,
        'settlements': settlements,
        'total_spent': total_spent,
        'remaining_budget': remaining_budget,
        'current_user_balance': current_user_balance,
    }
    return render(request, 'groups/group_detail.html', context)

@login_required
def accept_invitation_view(request, invitation_id):
    invitation = get_object_or_404(Invitation, id=invitation_id)

    if invitation.status != 'pending' or invitation.invited_email != request.user.email:
        messages.error(request, "Invalid or already processed invitation.")
        return redirect('groups:dashboard') # Changed redirect name

    with transaction.atomic():
        invitation.group.members.add(request.user)
        invitation.status = 'accepted'
        invitation.save()
    messages.success(request, f"You have joined the group '{invitation.group.name}'!")
    return redirect('groups:dashboard') # Changed redirect name

@login_required
def decline_invitation_view(request, invitation_id):
    invitation = get_object_or_404(Invitation, id=invitation_id)

    if invitation.status != 'pending' or invitation.invited_email != request.user.email:
        messages.error(request, "Invalid or already processed invitation.")
        return redirect('groups:dashboard') # Changed redirect name

    invitation.status = 'declined'
    invitation.save()
    messages.info(request, f"You have declined the invitation to '{invitation.group.name}'.")
    return redirect('groups:dashboard') # Changed redirect name

@login_required
def join_group_by_code(request):
    if request.method == 'POST':
        group_code = request.POST.get('group_code')

        if not group_code:
            messages.error(request, "Please enter a group code.")
            return redirect('groups:dashboard') # Changed redirect name

        try:
            group = Group.objects.get(id=group_code)
        except Group.DoesNotExist:
            messages.error(request, "Group not found with the provided code.")
            return redirect('groups:dashboard') # Changed redirect name
        except ValueError:
            messages.error(request, "Invalid group code format.")
            return redirect('groups:dashboard') # Changed redirect name

        if request.user in group.members.all():
            messages.info(request, f"You are already a member of '{group.name}'.")
            return redirect('groups:group_detail', group_id=group.id) # Changed redirect name

        with transaction.atomic():
            group.members.add(request.user)

            try:
                updated_member_ids = [str(member.id) for member in group.members.all()]

                response = supabase.table("groups") \
                    .update({"member_ids": updated_member_ids}) \
                    .eq("id", str(group.id)) \
                    .execute()

                if response.data:
                    messages.success(request, f"Successfully joined '{group.name}'!")
                else:
                    messages.warning(request, f"Joined group in Django, but failed to sync members with Supabase. Error: {response.error.message}")
                    raise Exception("Supabase group members sync failed")

            except Exception as e:
                messages.error(request, f"An error occurred while joining group and syncing with Supabase: {e}")
                raise

        return redirect('groups:group_detail', group_id=group.id) # Changed redirect name
    else:
        return redirect('groups:dashboard') # Changed redirect name

@login_required
def leave_group_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if group.created_by == request.user and group.members.count() == 1:
        messages.error(request, "You are the sole creator and member. You cannot leave the group. You must delete it instead.")
        return redirect('groups:group_detail', group_id=group.id) # Changed redirect name

    if request.user in group.members.all():
        with transaction.atomic():
            group.members.remove(request.user)

            try:
                updated_member_ids = [str(member.id) for member in group.members.all()]
                response = supabase.table("groups") \
                    .update({"member_ids": updated_member_ids}) \
                    .eq("id", str(group.id)) \
                    .execute()

                if response.data:
                    messages.success(request, f"You have left the group '{group.name}'.")
                else:
                    messages.warning(request, f"Left group in Django, but failed to sync members with Supabase. Error: {response.error.message}")
                    raise Exception("Supabase group member removal sync failed")

            except Exception as e:
                messages.error(request, f"An error occurred while leaving group and syncing with Supabase: {e}")
                raise

    else:
        messages.info(request, "You are not a member of this group.")

    return redirect('groups:dashboard') # Changed redirect name

@login_required
def delete_group_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if group.created_by != request.user:
        messages.error(request, "You are not authorized to delete this group.")
        return redirect('groups:group_detail', group_id=group.id) # Changed redirect name

    members = group.members.all()
    # Now importing Expense from expenses.models explicitly
    expenses = Expense.objects.filter(group=group) # Use Expense model from its app

    balances = {member.id: 0 for member in members}
    for expense in expenses:
        payer_id = expense.paid_by.id
        amount = expense.amount
        balances[payer_id] += amount
        if expense.participants.exists():
            share = amount / expense.participants.count()
            for participant in expense.participants.all():
                balances[participant.id] -= share

    if any(abs(balance) > 0.01 for balance in balances.values()):
        messages.error(request, "Cannot delete group: There are outstanding balances. Please settle all expenses first.")
        return redirect('groups:group_detail', group_id=group.id) # Changed redirect name

    with transaction.atomic():
        try:
            supabase_response = supabase.table("groups").delete().eq("id", str(group.id)).execute()

            if not supabase_response.data:
                 messages.warning(request, f"Group deleted in Django, but failed to delete from Supabase. Error: {supabase_response.error.message}")
                 raise Exception("Supabase group deletion failed")

            group_name = group.name
            group.delete()
            messages.success(request, f"Group '{group_name}' and all its associated data have been successfully deleted.")

        except Exception as e:
            messages.error(request, f"An error occurred during group deletion: {e}")
            raise

    return redirect('groups:dashboard') # Changed redirect name

@login_required
def share_group_link_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user not in group.members.all():
        messages.error(request, "You are not a member of this group.")
        return redirect('groups:dashboard') # Changed redirect name

    context = {
        'group': group,
    }
    return render(request, 'groups/link_sharing.html', context)
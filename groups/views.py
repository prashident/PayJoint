# groups/views.py
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q
from decimal import Decimal
from .utils import get_smart_insight

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
    # Optimization: Prefetch members and expenses to prevent slow loading
    user_groups = request.user.joined_groups.prefetch_related('members')

    total_owed_to_user = Decimal('0.00')
    total_user_owes = Decimal('0.00')
    groups_with_details = []

    for group in user_groups:
        # Optimization: Prefetch participants and settled_by
        expenses = Expense.objects.filter(group=group).prefetch_related('participants', 'settled_by')
        members = group.members.all()

        balances_in_group = {member.id: Decimal(0) for member in members}
        
        for expense in expenses:
            if not expense.participants.exists():
                continue
                
            share = expense.amount / Decimal(expense.participants.count())
            payer = expense.paid_by
            settled_member_ids = set(expense.settled_by.values_list('id', flat=True))

            for participant in expense.participants.all():
                # ONLY calculate balance if the participant hasn't settled yet
                if participant.id not in settled_member_ids:
                    if participant != payer:
                        balances_in_group[participant.id] -= share
                        balances_in_group[payer.id] += share

        user_balance_in_this_group = balances_in_group.get(request.user.id, Decimal(0))
        
        # 2. Update Global Totals
        if user_balance_in_this_group > 0:
            total_owed_to_user += user_balance_in_this_group
        elif user_balance_in_this_group < 0:
            total_user_owes += abs(user_balance_in_this_group)

        # 3. Enhanced Budget Logic
        total_spent = group.get_total_expenses_amount() # Matches 'total_spent' in template
        budget_limit = None
        
        # Determine the effective limit based on group settings
        if group.budget and group.budget > 0:
            budget_limit = group.budget
        elif group.group_type == 'Trip' and group.individual_budget:
            budget_limit = group.individual_budget * Decimal(group.members.count())
        elif group.group_type == 'Home' and group.monthly_home_budget:
            budget_limit = group.monthly_home_budget

        # Calculate percentage for the progress bar
        budget_percent = 0
        if budget_limit and budget_limit > 0:
            budget_percent = (total_spent / budget_limit) * 100
            # Cap at 100 so the progress bar doesn't overflow the UI
            budget_percent = min(float(budget_percent), 100.0)

        groups_with_details.append({
            'group': group,
            'user_balance': user_balance_in_this_group.quantize(Decimal('0.01')),
            'total_spent': total_spent.quantize(Decimal('0.01')),
            'budget_limit': budget_limit.quantize(Decimal('0.01')) if budget_limit else None,
            'budget_percent': round(budget_percent, 2), # Used by progress bar width
        })

    net_balance = total_owed_to_user - total_user_owes

    recent_activities = Expense.objects.filter(
        group__in=user_groups
    ).filter(
        Q(paid_by=request.user) | Q(participants=request.user)
    ).distinct().order_by('-created_at')[:6]

    smart_insight = get_smart_insight(request.user, groups_with_details)

    context = {
        'groups_with_details': groups_with_details,
        'smart_insight': smart_insight,
        'total_owed_to_user': total_owed_to_user.quantize(Decimal('0.01')),
        'total_user_owes': total_user_owes.quantize(Decimal('0.01')),
        'net_balance': net_balance.quantize(Decimal('0.01')),
        'recent_activities': recent_activities,
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

            return redirect('groups:dashboard')
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
        return redirect('groups:group_detail', group_id=group.id)

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

            return redirect('groups:group_detail', group_id=group.id)
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

    return render(request, 'groups/create_group_modal.html', {'form': form})

@login_required
def group_detail_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user not in group.members.all():
        messages.error(request, "You are not a member of this group.")
        return redirect('groups:dashboard')
    
    sort_option = request.GET.get('sort', 'latest')
    sort_order_map = {
        'latest': ['-created_at'],
        'payer': ['paid_by__username', '-created_at'],
        'type': ['category', '-created_at'],
    }
    order_by_fields = sort_order_map.get(sort_option, sort_order_map['latest'])


    # Optimization: prefetch participants and settled_by
    expenses = Expense.objects.filter(group=group).prefetch_related('participants', 'settled_by').order_by('-created_at')

    expenses = (
        Expense.objects.filter(group=group)
        .prefetch_related('participants', 'settled_by')
        .select_related('paid_by')
        .order_by(*order_by_fields)
    )


    members = group.members.all()

    member_spent = {member.id: Decimal('0.00') for member in members}
    for expense in expenses:
        member_spent[expense.paid_by.id] += expense.amount

    for member in members:
        member.total_spent_amount = member_spent.get(member.id, Decimal('0.00'))

    # --- DEFINE TOTAL SPENT HERE ---
    total_spent = group.get_total_expenses_amount() or Decimal('0.00')
    
    # Calculate remaining budget safely
    remaining_budget = None
    if group.budget and group.budget > 0:
        remaining_budget = group.budget - total_spent

    # 1. Dynamic Balance Calculation (excluding settled debts)
    balances = {member.id: Decimal('0.00') for member in members}
    for expense in expenses:
        if not expense.participants.exists():
            continue
            
        share = expense.amount / Decimal(expense.participants.count())
        payer = expense.paid_by
        settled_ids = set(expense.settled_by.values_list('id', flat=True))

        for participant in expense.participants.all():
            # If the specific split for this participant isn't settled
            if participant.id not in settled_ids:
                if participant != payer:
                    balances[participant.id] -= share
                    balances[payer.id] += share

    # 2. Settlement Algorithm
    settlements = []
    # Convert dict to lists for the greedy algorithm
    pos_balances = sorted([{'user': m, 'bal': balances[m.id]} for m in members if balances[m.id] > Decimal('0.01')], key=lambda x: x['bal'], reverse=True)
    neg_balances = sorted([{'user': m, 'bal': balances[m.id]} for m in members if balances[m.id] < Decimal('-0.01')], key=lambda x: x['bal'])

    i, j = 0, 0
    while i < len(neg_balances) and j < len(pos_balances):
        amount = min(abs(neg_balances[i]['bal']), pos_balances[j]['bal'])
        if amount > Decimal('0.01'):
            settlements.append({
                'from_user': neg_balances[i]['user'],
                'to_user': pos_balances[j]['user'],
                'amount': amount.quantize(Decimal('1')) # Clean UI rounding
            })
        neg_balances[i]['bal'] += amount
        pos_balances[j]['bal'] -= amount
        if abs(neg_balances[i]['bal']) < Decimal('0.01'): i += 1
        if abs(pos_balances[j]['bal']) < Decimal('0.01'): j += 1
    
    current_user_balance = balances.get(request.user.id, Decimal('0.00')).quantize(Decimal('0.01'))

    context = {
        'group': group,
        'expenses': expenses,
        'members': members,
        'settlements': settlements,
        'total_spent': total_spent, # This was missing!
        'remaining_budget': remaining_budget,
        'current_user_balance': current_user_balance,
    }
    return render(request, 'groups/group_detail.html', context)
    
@login_required
def accept_invitation_view(request, invitation_id):
    invitation = get_object_or_404(Invitation, id=invitation_id)

    if invitation.status != 'pending' or invitation.invited_email != request.user.email:
        messages.error(request, "Invalid or already processed invitation.")
        return redirect('groups:dashboard')

    with transaction.atomic():
        invitation.group.members.add(request.user)
        invitation.status = 'accepted'
        invitation.save()
    messages.success(request, f"You have joined the group '{invitation.group.name}'!")
    return redirect('groups:dashboard')

@login_required
def decline_invitation_view(request, invitation_id):
    invitation = get_object_or_404(Invitation, id=invitation_id)

    if invitation.status != 'pending' or invitation.invited_email != request.user.email:
        messages.error(request, "Invalid or already processed invitation.")
        return redirect('groups:dashboard')

    invitation.status = 'declined'
    invitation.save()
    messages.info(request, f"You have declined the invitation to '{invitation.group.name}'.")
    return redirect('groups:dashboard')

@login_required
def join_group(request):
    if request.method == 'POST':
        # Ensure we use .upper() to match the stored code
        input_code = request.POST.get('invite_code', '').strip().upper()

        if not input_code:
            messages.error(request, "Please enter an invite code.")
            return redirect('groups:dashboard')

        try:
            # ✅ CHANGE: Query by 'invite_code', not 'id'
            group = Group.objects.get(invite_code=input_code)
            
            if request.user in group.members.all():
                messages.info(request, f"You are already a member of '{group.name}'.")
                return redirect('groups:group_detail', group_id=group.id)

            with transaction.atomic():
                group.members.add(request.user)
                # Keep your existing Supabase sync logic here...
                
            messages.success(request, f"Successfully joined {group.name}!")
            return redirect('groups:group_detail', group_id=group.id)

        except Group.DoesNotExist:
            messages.error(request, f"Invalid invite code: {input_code}")
            return redirect('groups:dashboard')

    return redirect('groups:dashboard')

@login_required
def leave_group_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if group.created_by == request.user and group.members.count() == 1:
        messages.error(request, "You are the sole creator and member. You cannot leave the group. You must delete it instead.")
        return redirect('groups:group_detail', group_id=group.id)

    if request.user in group.members.all():
        with transaction.atomic():
            group.members.remove(request.user)

            try:
                updated_member_ids = [str(member.id) for member in group.members.all()]
                # Supabase `update` operation depends on synchronized Django and Supabase user IDs.
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

    return redirect('groups:dashboard')

@login_required
def delete_group_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if group.created_by != request.user:
        messages.error(request, "You are not authorized to delete this group.")
        return redirect('groups:group_detail', group_id=group.id)

    # 1. NEW DYNAMIC BALANCE CHECK (Checks only UNSETTLED debts)
    expenses = Expense.objects.filter(group=group).prefetch_related('participants', 'settled_by')
    members = group.members.all()
    balances = {member.id: Decimal('0.00') for member in members}

    for expense in expenses:
        if not expense.participants.exists():
            continue
            
        share = expense.amount / Decimal(expense.participants.count())
        payer = expense.paid_by
        settled_ids = set(expense.settled_by.values_list('id', flat=True))

        for participant in expense.participants.all():
            # ONLY count the debt if the participant HAS NOT settled it yet
            if participant.id not in settled_ids:
                if participant != payer:
                    balances[participant.id] -= share
                    balances[payer.id] += share

    # Check if ANY unsettled balance remains
    if any(abs(balance) > Decimal('0.01') for balance in balances.values()):
        messages.error(request, "Cannot delete group: There are outstanding balances. Please settle all expenses first.")
        return redirect('groups:group_detail', group_id=group.id)

    # 2. PROCEED TO DELETE (Your existing logic)
    with transaction.atomic():
        try:
            # Sync with Supabase
            supabase_response = supabase.table("groups").delete().eq("id", str(group.id)).execute()
            
            group_name = group.name
            group.delete()
            messages.success(request, f"Group '{group_name}' has been successfully deleted.")
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            raise

    return redirect('groups:dashboard')

@login_required
def share_group_link_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user not in group.members.all():
        messages.error(request, "You are not a member of this group.")
        return redirect('groups:dashboard')

    context = {
        'group': group,
    }
    return render(request, 'groups/link_sharing.html', context)


@login_required
def update_budget(request, group_id):
    if request.method == 'POST':
        group = get_object_or_404(Group, id=group_id)
        
        # Ensure only the creator/admin can change the budget
        if request.user == group.created_by:
            new_budget = request.POST.get('budget')
            if new_budget is not None:
                group.budget = new_budget
                group.save()
        
        return redirect('groups:group_detail', group_id=group.id)
    return redirect('groups:dashboard')
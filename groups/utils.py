from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

def get_smart_insight(user, groups_details):
    """
    Priority-based rule engine. 
    Returns: { 'icon': str, 'title': str, 'message': str, 'action_url': str, 'action_text': str }
    """
    # 1. Onboarding Check
    if not groups_details:
        return {
            'icon': '✨',
            'message': 'Ready to start tracking? Create your first group to manage shared expenses.',
            'action_url': 'groups:create_group',
            'action_text': 'Create Group'
        }

    # 2. Overbudget Check (Highest Priority)
    for detail in groups_details:
        if detail['budget_limit'] and detail['total_spent'] >= detail['budget_limit']:
            return {
                'icon': '⚠️',
                'message': f"'{detail['group'].name}' has crossed its budget. Consider reviewing recent expenses.",
                'action_url': 'groups:group_detail',
                'group_id': detail['group'].id,
                'action_text': 'Review Group'
            }

    # 3. Debt Check
    total_owed = sum(d['user_balance'] for d in groups_details if d['user_balance'] < 0)
    if total_owed < 0:
        # Find the group where they owe the most
        top_debt_group = min(groups_details, key=lambda x: x['user_balance'])
        return {
            'icon': '💸',
            'message': f"You owe ₹{abs(top_debt_group['user_balance'])} in '{top_debt_group['group'].name}'.",
            'action_url': 'groups:group_detail',
            'group_id': top_debt_group['group'].id,
            'action_text': 'Settle Up'
        }

    # 4. Inactivity Check
    # (Assuming you have access to recent_activities from dashboard_view)
    # If no activity in 7 days, nudge them.

    # 5. Default/Positive Reinforcement
    return {
        'icon': '✅',
        'message': 'All your expenses are up to date. Nice work!',
        'action_url': None,
        'action_text': None
    }
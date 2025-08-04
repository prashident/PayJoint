# groups/forms.py
from django import forms
from django.contrib.auth.models import User
# Import Group and Invitation from models within this same app
from .models import Group, Invitation

# Common widget attributes for consistent styling
COMMON_INPUT_ATTRS = {
    'class': 'w-full px-4 py-3 bg-[var(--accent-royal-blue-dark)] border border-[var(--accent-royal-blue-medium)] rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--highlight-gold-yellow-darker)] transition-shadow duration-300'
}

class GroupForm(forms.ModelForm):
    group_type = forms.ChoiceField(
        choices=Group.GROUP_TYPE_CHOICES,
        widget=forms.RadioSelect(),
        label="Group Type",
        initial='Others',
        required=True
    )

    set_individual_budget = forms.BooleanField(
        required=False,
        label="Set individual budgets"
    )

    class Meta:
        model = Group
        fields = ['name', 'description', 'image', 'budget', 'group_type', 'start_date', 'end_date', 'individual_budget', 'monthly_home_budget']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input-style',
                'placeholder': 'Group Name',
                'required': 'required',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input-style resize-none',
                'placeholder': 'Group Description (optional)'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'absolute inset-0 w-full h-full opacity-0 cursor-pointer'
            }),
            'budget': forms.NumberInput(attrs={
                'class': 'form-input-style',
                'placeholder': 'e.g., 5000.00 (Optional Budget)',
                'min': '0',
                'step': '0.01'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input-style'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input-style'
            }),
            'individual_budget': forms.NumberInput(attrs={
                'class': 'form-input-style',
                'placeholder': 'Enter individual budget',
                'min': '0',
                'step': '0.01'
            }),
            'monthly_home_budget': forms.NumberInput(attrs={
                'class': 'form-input-style',
                'placeholder': 'Enter monthly home budget',
                'min': '0',
                'step': '0.01'
            }),
        }
        labels = {
            'name': 'Group Name',
            'description': 'Description (Optional)',
            'image': 'Group Image',
            'budget': 'Group Budget (Optional)',
            'group_type': 'Group Type',
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'individual_budget': 'Individual Budget',
            'monthly_home_budget': 'Monthly Home Budget',
        }

    def clean(self):
        cleaned_data = super().clean()
        group_type = cleaned_data.get('group_type')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        budget = cleaned_data.get('budget')
        individual_budget = cleaned_data.get('individual_budget')
        monthly_home_budget = cleaned_data.get('monthly_home_budget')
        set_individual_budget = cleaned_data.get('set_individual_budget')

        if group_type == 'Trip':
            if not start_date:
                self.add_error('start_date', "Start date is required for Trip groups.")
            if not end_date:
                self.add_error('end_date', "End date is required for Trip groups.")
            if start_date and end_date and start_date > end_date:
                self.add_error('end_date', "End date cannot be before the start date.")

            if set_individual_budget and individual_budget is None:
                self.add_error('individual_budget', "Individual budget is required if 'Set individual budgets' is checked.")
            elif not set_individual_budget:
                cleaned_data['individual_budget'] = None
        else:
            cleaned_data['start_date'] = None
            cleaned_data['end_date'] = None
            cleaned_data['individual_budget'] = None
            cleaned_data['set_individual_budget'] = False

        if group_type == 'Home':
            pass
        else:
            cleaned_data['monthly_home_budget'] = None

        return cleaned_data

class InvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ['invited_email']
        widgets = {
            'invited_email': forms.EmailInput(attrs={
                'class': 'w-full rounded-lg border-2 border-[var(--royal-blue-medium)] bg-[var(--royal-blue-medium)] px-4 py-3 text-white placeholder-gray-400 focus:border-[var(--gold-yellow-highlight)] focus:outline-none focus:ring-0',
                'placeholder': 'friend@example.com'
            }),
        }
        labels = {
            'invited_email': 'Invitee Email',
        }

    def clean_invited_email(self):
        invited_email = self.cleaned_data['invited_email']
        return invited_email
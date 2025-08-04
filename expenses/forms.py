# expenses/forms.py
from django import forms
from django.contrib.auth.models import User
# Import Expense from models within this same app
from .models import Expense
# Import Group from the groups app
from groups.models import Group

class ExpenseForm(forms.ModelForm):
    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(), # This queryset will be set in the view
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'h-5 w-5 rounded border-[var(--accent-royal-blue-darker)] bg-[var(--accent-royal-blue)] text-[var(--highlight-gold-yellow)] focus:ring-[var(--highlight-gold-yellow)]'
        }),
        required=True,
        label="Split Between"
    )
    paid_by = forms.ModelChoiceField(
        queryset=User.objects.none(), # This queryset will be set in the view
        widget=forms.Select(attrs={
            'class': 'w-full h-12 px-4 bg-[var(--accent-royal-blue)] border border-[var(--accent-royal-blue-darker)] rounded-lg text-white focus:ring-[var(--highlight-gold-yellow)] focus:border-[var(--highlight-gold-yellow)] transition duration-300 appearance-none',
            'style': "background-image: url('data:image/svg+xml,%3csvg xmlns=%27http://www.w3.org/2000/svg%27 fill=%27none%27 viewBox=%270 0 20 20%27%3e%3cpath stroke=%27%23ffc300%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27 stroke-width=%271.5%27 d=%27m6 8 4 4 4-4%27/%3e%3c/svg%3e'); background-repeat: no-repeat; background-position: right 1rem center;"
        }),
        required=True,
        label="Paid By"
    )

    class Meta:
        model = Expense
        fields = ['description', 'amount', 'paid_by', 'participants']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'w-full h-12 px-4 bg-[var(--accent-royal-blue)] border border-[var(--accent-royal-blue-darker)] rounded-lg text-white focus:ring-[var(--highlight-gold-yellow)] focus:border-[var(--highlight-gold-yellow)] transition duration-300 placeholder:text-gray-500',
                'placeholder': 'e.g., Dinner with friends'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full h-12 pl-10 pr-4 bg-[var(--accent-royal-blue)] border border-[var(--accent-royal-blue-darker)] rounded-lg text-white focus:ring-[var(--highlight-gold-yellow)] focus:border-[var(--highlight-gold-yellow)] transition duration-300 placeholder:text-gray-500',
                'placeholder': '0'
            }),
        }
        labels = {
            'description': 'Expense Title',
            'amount': 'Amount',
        }
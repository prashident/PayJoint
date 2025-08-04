# users/forms.py
from django import forms
from django.contrib.auth.models import User

# Common widget attributes for consistent styling
COMMON_INPUT_ATTRS = {
    'class': 'w-full px-4 py-3 bg-[var(--accent-royal-blue-dark)] border border-[var(--accent-royal-blue-medium)] rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[var(--highlight-gold-yellow-darker)] transition-shadow duration-300'
}

class LoginForm(forms.Form):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={**COMMON_INPUT_ATTRS, 'placeholder': 'Enter your email'}),
        required=True
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={**COMMON_INPUT_ATTRS, 'placeholder': 'Your password'}),
        required=True
    )

class SignupForm(forms.Form):
    username = forms.CharField(
        label="Username",
        max_length=150,
        widget=forms.TextInput(attrs={**COMMON_INPUT_ATTRS, 'placeholder': 'Create a username'}),
        required=True
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={**COMMON_INPUT_ATTRS, 'placeholder': 'Enter your email'}),
        required=True
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={**COMMON_INPUT_ATTRS, 'placeholder': 'Create a Password'}),
        required=True
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={**COMMON_INPUT_ATTRS, 'placeholder': 'Confirm your password'}),
        required=True
    )
    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered. Please log in or use a different email.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')

        if password and password2 and password != password2:
            self.add_error('password2', "Passwords do not match.")
        return cleaned_data

class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-input block w-full rounded-md border-transparent px-4 py-3 text-base placeholder-gray-400 focus:border-transparent focus:ring-2 focus:ring-[var(--gold-yellow-primary)] focus:ring-offset-2 focus:ring-offset-[var(--background-deep-navy)] text-white bg-[var(--royal-blue-medium)]',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input block w-full rounded-md border-transparent px-4 py-3 text-base placeholder-gray-400 focus:border-transparent focus:ring-2 focus:ring-[var(--gold-yellow-primary)] focus:ring-offset-2 focus:ring-offset-[var(--background-deep-navy)] text-white bg-[var(--royal-blue-medium)]',
                'placeholder': 'Last Name'
            }),
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
        }
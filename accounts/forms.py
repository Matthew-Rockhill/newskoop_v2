# accounts/forms.py
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import CustomUser, RadioStation

class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'block w-full pl-10 rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary-100 focus:ring-opacity-50',
        'placeholder': 'Email Address'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'block w-full pl-10 rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary-100 focus:ring-opacity-50',
        'placeholder': 'Password'
    }))
class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'mobile_number']

class StaffUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    
    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'first_name', 'last_name', 'mobile_number', 'staff_role', 'is_active']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Only check for duplicate emails if this is a new user
        if not self.instance.pk and CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

class RadioUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    radio_station = forms.ModelChoiceField(queryset=RadioStation.objects.filter(is_active=True), required=True)
    is_primary_contact = forms.BooleanField(required=False)
    
    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'first_name', 'last_name', 'mobile_number', 'radio_station', 'is_primary_contact', 'is_active']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Only check for duplicate emails if this is a new user
        if not self.instance.pk and CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        is_primary = cleaned_data.get('is_primary_contact')
        station = cleaned_data.get('radio_station')
        
        # If this user is being set as primary, check for existing primary contacts
        if is_primary and station and not self.instance.pk:  # For new users only
            if CustomUser.objects.filter(radio_station=station, is_primary_contact=True).exists():
                self.add_error('is_primary_contact', 'This station already has a primary contact. Only one primary contact is allowed per station.')
        
        return cleaned_data

class StationForm(forms.ModelForm):
    class Meta:
        model = RadioStation
        fields = [
            'name', 'description', 'province', 'contact_number',
            'contact_email', 'website', 'is_active', 'religion_access',
            'access_english', 'access_afrikaans', 'access_xhosa',
            'access_news_stories', 'access_news_bulletins', 'access_sport',
            'access_finance', 'access_specialty'
        ]

class PasswordResetForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True)
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('confirm_password'):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

class ChangePasswordForm(PasswordChangeForm):
    pass  # Uses Django’s built-in password change form

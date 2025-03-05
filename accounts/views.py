# accounts/views.py
import logging
from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .models import CustomUser, RadioStation
from .forms import (
    LoginForm, ProfileForm, StaffUserForm, RadioUserForm,
    StationForm, PasswordResetForm, ChangePasswordForm
)

logger = logging.getLogger(__name__)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        user = authenticate(request, username=email, password=password)
        if user:
            if not user.is_active:
                messages.error(request, 'Your account is inactive. Please contact an administrator.')
            else:
                auth_login(request, user)
                messages.success(request, 'Login successful.')
                return redirect('accounts:dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def logout_view(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('accounts:login')

@login_required
def dashboard_view(request):
    if request.user.user_type == CustomUser.UserType.STAFF:
        stats = {
            'active_users': CustomUser.objects.filter(is_active=True).count(),
            'active_stations': RadioStation.objects.filter(is_active=True).count(),
        }
    else:
        stats = {}
    return render(request, 'accounts/dashboard.html', {'stats': stats})

@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileForm(instance=user)
    return render(request, 'accounts/profile.html', {'form': form, 'user': user})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = ChangePasswordForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been updated successfully.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ChangePasswordForm(user=request.user)
    return render(request, 'accounts/change_password.html', {'form': form})

# Station management (for staff users)
@login_required
def station_list(request):
    if request.user.user_type != CustomUser.UserType.STAFF:
        raise PermissionDenied
    stations = RadioStation.objects.all().order_by('name')
    search_query = request.GET.get('q', '')
    province_filter = request.GET.get('province', '')
    status_filter = request.GET.get('status', '')
    if search_query:
        stations = stations.filter(name__icontains=search_query)
    if province_filter:
        stations = stations.filter(province=province_filter)
    if status_filter:
        is_active = (status_filter == 'active')
        stations = stations.filter(is_active=is_active)
    context = {
        'stations': stations,
        'search_query': search_query,
        'province_filter': province_filter,
        'status_filter': status_filter,
        'provinces': RadioStation.Province.choices,
    }
    return render(request, 'accounts/stations/station_list.html', context)

@login_required
def station_create(request):
    if request.user.user_type != CustomUser.UserType.STAFF:
        raise PermissionDenied
    if request.method == 'POST':
        form = StationForm(request.POST)
        # Extract primary contact details from POST
        primary_email = request.POST.get('primary_contact_email', '').strip()
        primary_password = request.POST.get('primary_contact_password', '').strip()
        primary_first_name = request.POST.get('primary_contact_first_name', '').strip()
        primary_last_name = request.POST.get('primary_contact_last_name', '').strip()
        primary_mobile = request.POST.get('primary_contact_mobile', '').strip()
        if form.is_valid():
            # Ensure primary contact fields are provided
            if not primary_email or not primary_password:
                messages.error(request, 'Primary contact email and password are required.')
                return render(request, 'accounts/stations/station_create.html', {'form': form})
            station = form.save()
            try:
                # Create the primary user associated with the station
                primary_user = CustomUser.objects.create_user(
                    email=primary_email,
                    password=primary_password,
                    first_name=primary_first_name,
                    last_name=primary_last_name,
                    mobile_number=primary_mobile,
                    user_type=CustomUser.UserType.RADIO,
                    radio_station=station,
                    is_primary_contact=True,
                    is_active=station.is_active
                )
            except Exception as e:
                messages.error(request, f'Error creating primary user: {str(e)}')
                station.delete()  # Roll back station creation if needed
                return render(request, 'accounts/stations/station_create.html', {'form': form})
            messages.success(request, f'Radio station "{station.name}" and its primary user created successfully.')
            return redirect('accounts:station_detail', station_id=station.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StationForm()
    return render(request, 'accounts/stations/station_create.html', {'form': form})


@login_required
def station_edit(request, station_id):
    if request.user.user_type != CustomUser.UserType.STAFF:
        raise PermissionDenied
    station = get_object_or_404(RadioStation, id=station_id)
    if request.method == 'POST':
        form = StationForm(request.POST, instance=station)
        if form.is_valid():
            form.save()
            messages.success(request, f'Station "{station.name}" updated successfully.')
            return redirect('accounts:station_detail', station_id=station.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StationForm(instance=station)
    return render(request, 'accounts/stations/station_edit.html', {'form': form, 'station': station})

@login_required
def station_detail(request, station_id):
    if request.user.user_type != CustomUser.UserType.STAFF:
        raise PermissionDenied
    station = get_object_or_404(RadioStation, id=station_id)
    users = station.users.all().order_by('-is_primary_contact', 'email')
    return render(request, 'accounts/stations/station_detail.html', {'station': station, 'users': users})

@login_required
def station_delete(request, station_id):
    if request.user.user_type != CustomUser.UserType.STAFF:
        raise PermissionDenied
    station = get_object_or_404(RadioStation, id=station_id)
    if request.method == 'POST':
        confirmation = request.POST.get('confirmation', '')
        if confirmation == station.name:
            station.delete()
            messages.success(request, f'Station "{station.name}" deleted successfully.')
            return redirect('accounts:station_list')
        else:
            messages.error(request, 'Confirmation text does not match.')
    return render(request, 'accounts/stations/station_delete_confirm.html', {'station': station})

# User management views
@login_required
def user_list(request):
    if request.user.user_type != CustomUser.UserType.STAFF:
        raise PermissionDenied
    user_type = request.GET.get('user_type', 'STAFF')
    if user_type == 'STAFF':
        users = CustomUser.objects.filter(user_type=CustomUser.UserType.STAFF)
    else:
        users = CustomUser.objects.filter(user_type=CustomUser.UserType.RADIO)
    search_query = request.GET.get('q', '')
    if search_query:
        users = users.filter(email__icontains=search_query)
    role_filter = request.GET.get('role', '')
    station_filter = request.GET.get('station', '')
    status_filter = request.GET.get('status', '')
    if role_filter and user_type == 'STAFF':
        users = users.filter(staff_role=role_filter)
    if station_filter and user_type == 'RADIO':
        users = users.filter(radio_station__id=station_filter)
    if status_filter:
        is_active = (status_filter == 'active')
        users = users.filter(is_active=is_active)
    context = {
        'users': users,
        'search_query': search_query,
        'role_filter': role_filter,
        'station_filter': station_filter,
        'status_filter': status_filter,
        'user_type': user_type,
    }
    return render(request, 'accounts/users/user_list.html', context)

@login_required
def create_staff_user(request):
    if request.user.user_type != CustomUser.UserType.STAFF:
        raise PermissionDenied
    if request.method == 'POST':
        form = StaffUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = CustomUser.UserType.STAFF
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, f'Staff user "{user.email}" created successfully.')
            return redirect('accounts:user_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffUserForm()
    return render(request, 'accounts/users/create_staff_user.html', {'form': form})

@login_required
def create_radio_user(request):
    if request.user.user_type != CustomUser.UserType.STAFF:
        raise PermissionDenied
    if request.method == 'POST':
        form = RadioUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = CustomUser.UserType.RADIO
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, f'Radio user "{user.email}" created successfully.')
            return redirect('accounts:user_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RadioUserForm()
    return render(request, 'accounts/users/create_radio_user.html', {'form': form})

@login_required
def edit_user(request, user_id):
    if request.user.user_type != CustomUser.UserType.STAFF:
        raise PermissionDenied
    user_obj = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        if user_obj.user_type == CustomUser.UserType.STAFF:
            form = StaffUserForm(request.POST, instance=user_obj)
            form.fields['email'].disabled = True
            # Remove password field so it isn’t validated
            form.fields.pop('password', None)
        else:
            form = RadioUserForm(request.POST, instance=user_obj)
            form.fields['email'].disabled = True
            form.fields.pop('password', None)
        if form.is_valid():
            form.save()
            messages.success(request, f'User "{user_obj.email}" updated successfully.')
            return redirect('accounts:user_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        if user_obj.user_type == CustomUser.UserType.STAFF:
            form = StaffUserForm(instance=user_obj)
            form.fields['email'].disabled = True
            form.fields.pop('password', None)
        else:
            form = RadioUserForm(instance=user_obj)
            form.fields['email'].disabled = True
            form.fields.pop('password', None)
    return render(request, 'accounts/users/edit_user.html', {'form': form, 'user_obj': user_obj})

@login_required
def delete_user(request, user_id):
    if request.user.user_type != CustomUser.UserType.STAFF:
        raise PermissionDenied
    user_obj = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        confirmation = request.POST.get('confirmation', '')
        if confirmation == user_obj.email:
            user_obj.delete()
            messages.success(request, f'User "{user_obj.email}" deleted successfully.')
            return redirect('accounts:user_list')
        else:
            messages.error(request, 'Confirmation email does not match.')
    return render(request, 'accounts/users/delete_user_confirm.html', {'user_obj': user_obj})

@login_required
def reset_password(request, user_id):
    if request.user.user_type != CustomUser.UserType.STAFF:
        raise PermissionDenied
    user_obj = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            user_obj.set_password(form.cleaned_data['password'])
            user_obj.save()
            messages.success(request, f'Password for "{user_obj.email}" reset successfully.')
            return redirect('accounts:user_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordResetForm()
    return render(request, 'accounts/users/reset_password.html', {'form': form, 'user_obj': user_obj})

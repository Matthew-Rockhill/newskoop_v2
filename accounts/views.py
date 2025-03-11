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
    # Initialize stats and activities
    stats = {}
    activities = []
    
    # Import datetime for calculations
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # Define time periods for comparison
    now = timezone.now()
    last_month_end = now - timedelta(days=30)
    last_month_start = now - timedelta(days=60)
    
    # For staff users, show more detailed statistics
    if request.user.user_type == CustomUser.UserType.STAFF:
        # Calculate current active users
        current_active_users = CustomUser.objects.filter(is_active=True).count()
        
        # Calculate active users last month (users who existed and were active 30 days ago)
        last_month_active_users = CustomUser.objects.filter(
            date_joined__lte=last_month_end,
            is_active=True
        ).count()
        
        # Calculate percentage change for users
        if last_month_active_users > 0:
            user_change_percentage = ((current_active_users - last_month_active_users) / last_month_active_users) * 100
        else:
            user_change_percentage = 100  # If there were no users last month, consider it 100% growth
        
        # Calculate current active stations
        current_active_stations = RadioStation.objects.filter(is_active=True).count()
        
        # Calculate active stations last month
        last_month_active_stations = RadioStation.objects.filter(
            created_at__lte=last_month_end,
            is_active=True
        ).count()
        
        # Calculate percentage change for stations
        if last_month_active_stations > 0:
            station_change_percentage = ((current_active_stations - last_month_active_stations) / last_month_active_stations) * 100
        else:
            station_change_percentage = 100  # If there were no stations last month, consider it 100% growth
            
        # Format the percentage strings with + or - sign
        user_change_str = f"{'+' if user_change_percentage >= 0 else ''}{user_change_percentage:.1f}%"
        station_change_str = f"{'+' if station_change_percentage >= 0 else ''}{station_change_percentage:.1f}%"
        
        # Populate stats dictionary
        stats = {
            'active_users': current_active_users,
            'active_stations': current_active_stations,
            'user_change': user_change_str,
            'station_change': station_change_str,
        }
        
        # Gather recent activity data - this would normally come from an activity log model
        # For now we'll create sample activities based on recent user and station activity
        
        # Get recent user creations/updates
        recent_users = CustomUser.objects.order_by('-date_joined')[:3]
        for user in recent_users:
            if user.date_joined:
                # Format timesince to be more readable
                from django.utils.timesince import timesince
                time_ago = timesince(user.date_joined) + " ago"
                
                activities.append({
                    'icon': 'user' if user.user_type == 'STAFF' else 'radio',
                    'icon_bg': 'primary',
                    'title': f"{user.get_full_name()} account created",
                    'subtitle': f"{time_ago} • {'Staff User' if user.user_type == 'STAFF' else 'Radio User'}"
                })
        
        # Get recent station creations/updates
        recent_stations = RadioStation.objects.order_by('-created_at')[:2]
        for station in recent_stations:
            if station.created_at:
                from django.utils.timesince import timesince
                time_ago = timesince(station.created_at) + " ago"
                
                activities.append({
                    'icon': 'radio',
                    'icon_bg': 'success',
                    'title': f"Radio station added: \"{station.name}\"",
                    'subtitle': f"{time_ago} • {station.get_province_display()}"
                })
    
    else:
        # For radio users, show more limited statistics
        if request.user.radio_station:
            # Calculate current active users for this station
            current_station_users = CustomUser.objects.filter(
                radio_station=request.user.radio_station,
                is_active=True
            ).count()
            
            # Calculate active users last month for this station
            last_month_station_users = CustomUser.objects.filter(
                radio_station=request.user.radio_station,
                date_joined__lte=last_month_end,
                is_active=True
            ).count()
            
            # Calculate percentage change for users
            if last_month_station_users > 0:
                user_change_percentage = ((current_station_users - last_month_station_users) / last_month_station_users) * 100
                user_change_str = f"{'+' if user_change_percentage >= 0 else ''}{user_change_percentage:.1f}%"
            elif current_station_users > 0:
                user_change_str = "+100%"  # If there were no users last month but there are now
            else:
                user_change_str = "0%"  # If there are no users now
            
            stats = {
                'active_users': current_station_users,
                'user_change': user_change_str,
            }
            
            # Show station-specific activities
            station_users = CustomUser.objects.filter(
                radio_station=request.user.radio_station
            ).order_by('-date_joined')[:5]
            
            for user in station_users:
                if user.date_joined:
                    from django.utils.timesince import timesince
                    time_ago = timesince(user.date_joined) + " ago"
                    
                    title = f"{user.get_full_name()} joined"
                    if user.is_primary_contact:
                        title += " as primary contact"
                    
                    activities.append({
                        'icon': 'user',
                        'icon_bg': 'primary',
                        'title': title,
                        'subtitle': f"{time_ago} • {request.user.radio_station.name}"
                    })
    
    return render(request, 'accounts/dashboard.html', {
        'stats': stats,
        'activities': activities
    })

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
    old_is_active = station.is_active
    
    if request.method == 'POST':
        form = StationForm(request.POST, instance=station)
        
        # Debug: Print the form data
        logger.debug(f"Station Edit Form Data: {request.POST}")
        
        if not form.is_valid():
            # Debug: Print form errors
            logger.error(f"Station form validation errors: {form.errors}")
            messages.error(request, 'Please correct the errors below.')
        else:
            updated_station = form.save()
            
            # If station active status changed, update users accordingly
            if old_is_active != updated_station.is_active:
                # For deactivating a station, deactivate all its users
                if not updated_station.is_active:
                    affected_users = CustomUser.objects.filter(radio_station=updated_station, is_active=True)
                    count = affected_users.count()
                    affected_users.update(is_active=False)
                    if count > 0:
                        messages.info(request, f'{count} users associated with this station have been deactivated.')
            
            messages.success(request, f'Station "{station.name}" updated successfully.')
            return redirect('accounts:station_detail', station_id=station.id)
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
            # Deactivate all users associated with this station before deleting
            station_users = CustomUser.objects.filter(radio_station=station)
            station_users.update(is_active=False)
            
            # Now delete the station
            station.delete()
            
            messages.success(request, f'Station "{station.name}" deleted successfully. All associated users have been deactivated.')
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
        # Add staff_roles to context for the dropdown
        staff_roles = CustomUser.StaffRole.choices
    else:
        users = CustomUser.objects.filter(user_type=CustomUser.UserType.RADIO)
        # Add stations to context for the dropdown
        
    
    search_query = request.GET.get('q', '')
    if search_query:
        # Fix search to include names, not just email
        from django.db.models import Q
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
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
    
    # Create context with all required data
    context = {
        'users': users,
        'search_query': search_query,
        'role_filter': role_filter,
        'station_filter': station_filter,
        'status_filter': status_filter,
        'user_type': user_type,
    }
    
    # Add the appropriate dropdown data based on user_type
    if user_type == 'STAFF':
        context['staff_roles'] = CustomUser.StaffRole.choices
    else:
        context['stations'] = RadioStation.objects.all().order_by('name')
    
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
    
    # Check if a station ID was provided in the URL
    station_id = request.GET.get('station')
    initial_data = {}
    
    if station_id:
        try:
            # Try to get the station to pre-select it
            station = RadioStation.objects.get(id=station_id)
            initial_data['radio_station'] = station
        except (RadioStation.DoesNotExist, ValueError):
            # If the station doesn't exist or ID is invalid, just continue without pre-selection
            pass
    
    if request.method == 'POST':
        form = RadioUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = CustomUser.UserType.RADIO
            user.set_password(form.cleaned_data['password'])
            
            # If this user is primary, ensure no other users for this station are primary
            if user.is_primary_contact and user.radio_station:
                CustomUser.objects.filter(
                    radio_station=user.radio_station, 
                    is_primary_contact=True
                ).update(is_primary_contact=False)
                
            user.save()
            messages.success(request, f'Radio user "{user.email}" created successfully.')
            
            # Redirect back to the station detail page if coming from there
            if station_id:
                return redirect('accounts:station_detail', station_id=station_id)
            return redirect('accounts:user_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RadioUserForm(initial=initial_data)
    
    return render(request, 'accounts/users/create_radio_user.html', {'form': form})

@login_required
def edit_user(request, user_id):
    if request.user.user_type != CustomUser.UserType.STAFF:
        raise PermissionDenied
    
    user_obj = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        if user_obj.user_type == CustomUser.UserType.STAFF:
            # For staff users
            form = StaffUserForm(request.POST, instance=user_obj)
            # Instead of disabling the email field, we'll make it readonly in the template
            # and exclude it from validation here
            if 'email' in form.fields:
                form.fields['email'].required = False
            if 'password' in form.fields:
                form.fields.pop('password', None)
        else:
            # For radio users
            form = RadioUserForm(request.POST, instance=user_obj)
            if 'email' in form.fields:
                form.fields['email'].required = False
            if 'password' in form.fields:
                form.fields.pop('password', None)
            
            # Check primary contact status
            new_is_primary = request.POST.get('is_primary_contact') == 'on'
            new_station_id = request.POST.get('radio_station')
            
            # If becoming primary and station changed or wasn't primary before
            if new_is_primary and (not user_obj.is_primary_contact or (new_station_id and str(user_obj.radio_station.id) != new_station_id)):
                try:
                    station = RadioStation.objects.get(id=new_station_id)
                    if CustomUser.objects.filter(radio_station=station, is_primary_contact=True).exclude(id=user_obj.id).exists():
                        form.add_error('is_primary_contact', 'This station already has a primary contact. Only one primary contact is allowed per station.')
                except Exception as e:
                    # If the station doesn't exist or there's any other error
                    logger.error(f"Error checking primary contact: {str(e)}")
        
        if form.is_valid():
            # Don't update the email field - keep the original
            user = form.save(commit=False)
            user.email = user_obj.email  # Preserve the original email
            user.save()
            
            # If this is a radio user being set as primary, ensure no other users for this station are primary
            if user.user_type == CustomUser.UserType.RADIO and user.is_primary_contact and user.radio_station:
                CustomUser.objects.filter(
                    radio_station=user.radio_station, 
                    is_primary_contact=True
                ).exclude(id=user.id).update(is_primary_contact=False)
                
            messages.success(request, f'User "{user_obj.email}" updated successfully.')
            return redirect('accounts:user_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # GET request - display the form
        if user_obj.user_type == CustomUser.UserType.STAFF:
            form = StaffUserForm(instance=user_obj)
            if 'password' in form.fields:
                form.fields.pop('password', None)
        else:
            form = RadioUserForm(instance=user_obj)
            if 'password' in form.fields:
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

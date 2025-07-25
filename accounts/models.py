# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import uuid
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        
        if self.model.objects.filter(email=email).exists():
            raise ValueError('A user with this email already exists.')
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        
        # Fix for the uppercase/lowercase user_type check
        if user.user_type == self.model.UserType.RADIO and not user.radio_station:
            raise ValueError("Radio users must be assigned to a radio station.")
        
        user.full_clean()  # Validate before saving
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'STAFF')
        extra_fields.setdefault('staff_role', 'SUPERADMIN')  # Set the SUPERADMIN role

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)

class RadioStation(models.Model):
    class Province(models.TextChoices):
        EASTERN_CAPE = 'EASTERN_CAPE', 'Eastern Cape'
        FREE_STATE = 'FREE_STATE', 'Free State'
        GAUTENG = 'GAUTENG', 'Gauteng'
        KWAZULU_NATAL = 'KWAZULU_NATAL', 'KwaZulu-Natal'
        LIMPOPO = 'LIMPOPO', 'Limpopo'
        MPUMALANGA = 'MPUMALANGA', 'Mpumalanga'
        NORTHERN_CAPE = 'NORTHERN_CAPE', 'Northern Cape'
        NORTH_WEST = 'NORTH_WEST', 'North West'
        WESTERN_CAPE = 'WESTERN_CAPE', 'Western Cape'
        NATIONAL = 'NATIONAL', 'National'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    province = models.CharField(max_length=20, choices=Province.choices, default=Province.GAUTENG)
    contact_number = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Access fields for content and permissions
    RELIGION_CHOICES = [
        ('GENERAL_ONLY', 'General Only'),
        ('GENERAL_PLUS_CHRISTIAN', 'General + Christian'),
        ('GENERAL_PLUS_MUSLIM', 'General + Muslim'),
    ]
    religion_access = models.CharField(max_length=25, choices=RELIGION_CHOICES, default='GENERAL_ONLY')
    access_english = models.BooleanField(default=True)
    access_afrikaans = models.BooleanField(default=False)
    access_xhosa = models.BooleanField(default=False)
    access_news_stories = models.BooleanField(default=False)
    access_news_bulletins = models.BooleanField(default=False)
    access_sport = models.BooleanField(default=False)
    access_finance = models.BooleanField(default=False)
    access_specialty = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        old_is_active = None
        old_access_permissions = None
        
        if not is_new:
            try:
                old = RadioStation.objects.get(pk=self.pk)
                old_is_active = old.is_active
                old_access_permissions = {
                    'news_stories': old.access_news_stories,
                    'news_bulletins': old.access_news_bulletins,
                    'sport': old.access_sport,
                    'finance': old.access_finance,
                    'specialty': old.access_specialty
                }
            except RadioStation.DoesNotExist:
                pass

        try:
            super().save(*args, **kwargs)
            
            # Log the action
            if is_new:
                logger.info(
                    f"New radio station created: {self.name} (ID: {self.id}) "
                    f"in {self.get_province_display()}"
                )
            else:
                changes = []
                if old_is_active != self.is_active:
                    changes.append(f"active status from {old_is_active} to {self.is_active}")
                
                # Check for changes in access permissions
                new_access_permissions = {
                    'news_stories': self.access_news_stories,
                    'news_bulletins': self.access_news_bulletins,
                    'sport': self.access_sport,
                    'finance': self.access_finance,
                    'specialty': self.access_specialty
                }
                
                for key, old_value in old_access_permissions.items():
                    if old_value != new_access_permissions[key]:
                        changes.append(f"{key} access from {old_value} to {new_access_permissions[key]}")
                
                if changes:
                    logger.info(
                        f"Radio station updated: {self.name} (ID: {self.id}) - "
                        f"Changed {', '.join(changes)}"
                    )
                else:
                    logger.debug(
                        f"Radio station updated: {self.name} (ID: {self.id})"
                    )
                    
        except Exception as e:
            logger.error(
                f"Error saving radio station {self.name}: {str(e)}",
                exc_info=True
            )
            raise

    def delete(self, *args, **kwargs):
        try:
            station_name = self.name
            station_id = self.id
            user_count = self.users.count()
            super().delete(*args, **kwargs)
            logger.info(
                f"Radio station deleted: {station_name} (ID: {station_id}) "
                f"with {user_count} associated users"
            )
        except Exception as e:
            logger.error(
                f"Error deleting radio station {self.name}: {str(e)}",
                exc_info=True
            )
            raise

class CustomUser(AbstractBaseUser, PermissionsMixin):
    class UserType(models.TextChoices):
        STAFF = 'STAFF', 'Newskoop Staff'
        RADIO = 'RADIO', 'Radio Station Staff'

    class StaffRole(models.TextChoices):
        SUPERADMIN = 'SUPERADMIN', 'Super Admin'
        ADMIN = 'ADMIN', 'Admin'
        EDITOR = 'EDITOR', 'Editor'
        SUB_EDITOR = 'SUB_EDITOR', 'Sub Editor'
        JOURNALIST = 'JOURNALIST', 'Journalist'
        INTERN = 'INTERN', 'Intern'
        

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    is_primary_contact = models.BooleanField(
        default=False,
        help_text="Designates whether this user is the primary contact for a radio station."
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    user_type = models.CharField(max_length=10, choices=UserType.choices, default=UserType.STAFF)
    staff_role = models.CharField(max_length=20, choices=StaffRole.choices, blank=True, null=True)
    # RADIO users must have a station
    radio_station = models.ForeignKey(RadioStation, on_delete=models.SET_NULL, blank=True, null=True, related_name='users')
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def clean(self):
        if self.user_type == CustomUser.UserType.RADIO and not self.radio_station:
            raise ValidationError("Radio users must be assigned to a radio station.")

    def get_full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.email

    def __str__(self):
        return self.email

    objects = CustomUserManager()

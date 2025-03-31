import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DATABASE_NAME', 'newskoop'),
        'USER': os.getenv('DATABASE_USER', 'nksuper'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD', 'Nk195330Db#'),
        'HOST': os.getenv('DATABASE_HOST', 'localhost'),
        'PORT': os.getenv('DATABASE_PORT', '5432'),
    }
}
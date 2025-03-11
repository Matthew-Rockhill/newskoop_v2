#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Building Tailwind CSS..."
python manage.py tailwind install
python manage.py tailwind build

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Build completed successfully!"
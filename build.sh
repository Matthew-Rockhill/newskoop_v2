#!/usr/bin/env bash
# exit on error
set -o errexit

# Install python dependencies
pip install -r requirements.txt

# Install Node.js dependencies and build Tailwind CSS
cd theme/static_src
npm install
npm run build
cd ../..

# Run Django migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --no-input
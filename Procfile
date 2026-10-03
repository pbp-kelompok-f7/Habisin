release: python manage.py migrate --noinput
web: gunicorn habisin.wsgi:application --bind 0.0.0.0:$PORT

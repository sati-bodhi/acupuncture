"""
WSGI config for webapp project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp.settings')
sys.path.insert(1, "/home/sati/anaconda3/envs/acupuncture/lib/python3.10/site-packages")
django.setup()

application = get_wsgi_application()

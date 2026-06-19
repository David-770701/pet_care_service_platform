import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pet_service_project.settings')

application = get_wsgi_application()

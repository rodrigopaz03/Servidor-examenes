from google.cloud import firestore
from django.conf import settings

db = firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)

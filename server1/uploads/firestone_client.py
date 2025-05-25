from google.cloud import firestore
from django.conf import settings

db = firestore.Client(
    project="exalted-booster-454620-j9",
    database="db-imagenes"
)
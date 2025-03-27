from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Imagen
from django.conf import settings
from google.cloud import storage
import uuid
import os

def upload_to_gcs(file_obj, filename, content_type):
    """
    Sube el archivo a GCS y retorna la URL pública
    """
    # Lógica inteligente: si estás local, usa JSON key; si no, usa default credentials (en GCP)
    if hasattr(settings, 'GCS_CREDENTIALS_FILE'):
        client = storage.Client.from_service_account_json(settings.GCS_CREDENTIALS_FILE)
    else:
        client = storage.Client()

    bucket = client.bucket(settings.GCS_BUCKET_NAME)

    blob_name = f'uploads/{uuid.uuid4()}_{filename}'
    blob = bucket.blob(blob_name)

    blob.upload_from_file(file_obj, content_type=content_type)
    blob.make_public()

    return blob.public_url

@csrf_exempt
def upload_imagen(request):
    if request.method == 'POST':
        archivo = request.FILES.get('imagen')
        if archivo:
            if not archivo.content_type.startswith('image/'):
                return JsonResponse({'error': 'El archivo subido no es una imagen'}, status=400)
            try:
                # Reiniciar el puntero del archivo si fue leído antes
                archivo.seek(0)
                public_url = upload_to_gcs(archivo, archivo.name, archivo.content_type)

                imagen_obj = Imagen.objects.create(
                    titulo=archivo.name,
                    url_archivo=public_url,
                    content_type=archivo.content_type,
                    ensamblada=False
                )
                return JsonResponse({
                    'msg': 'Imagen almacenada en GCS',
                    'id': imagen_obj.id,
                    'url': public_url
                }, status=201)
            except Exception as e:
                return JsonResponse({'error': f'Fallo en subida a GCS: {str(e)}'}, status=500)
        else:
            return JsonResponse({'error': 'No se recibió ningún archivo'}, status=400)
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@csrf_exempt
def serve_imagen(request, imagen_id):
    try:
        imagen_obj = Imagen.objects.get(id=imagen_id)
    except Imagen.DoesNotExist:
        return HttpResponse("Imagen no encontrada", status=404)

    return JsonResponse({'url': imagen_obj.url_archivo})

@csrf_exempt
def health_check(request):
    return HttpResponse('ok')

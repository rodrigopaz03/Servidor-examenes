import json
from concurrent.futures import ThreadPoolExecutor
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from google.cloud import storage
from .models import Imagen

executor = ThreadPoolExecutor(max_workers=16)

# Función para subir archivo a Google Cloud Storage
def upload_to_gcs(file_data, destination_blob_name, content_type):
    client = storage.Client()
    bucket_name = 'arquisoft-bucket'
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_string(file_data, content_type=content_type)
    blob.make_public()  

    return blob.public_url

@csrf_exempt
def upload_imagen(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    archivo = request.FILES.get('imagen')

    if not archivo:
        return JsonResponse({'error': 'No se recibió ningún archivo en FILES'}, status=400)

    titulo = archivo.name
    content_type = archivo.content_type
    archivo_data = archivo.read()

    def process_image(titulo, content_type, archivo_data):
        try:
            # Crear registro inicial en la base de datos
            imagen_obj = Imagen.objects.create(titulo=titulo, content_type=content_type)

            # Nombre único en GCS
            destination_blob_name = f'imagenes/{imagen_obj.id}_{titulo}'

            # Subir imagen completa a Google Cloud Storage
            public_url = upload_to_gcs(archivo_data, destination_blob_name, content_type)

            # Guardar el link generado en la base de datos
            imagen_obj.url_gcp = public_url
            imagen_obj.save()

        except Exception as e:
            print(f"Error procesando imagen: {e}")

    # Ejecutar la tarea en segundo plano para no bloquear la respuesta
    executor.submit(process_image, titulo, content_type, archivo_data)

    return JsonResponse({
        'msg': 'Imagen recibida y en proceso de subida a GCS',
        'nota': 'La imagen se procesará y subirá en segundo plano a Google Cloud Storage.'
    }, status=202)


def serve_imagen(request, imagen_id):
    try:
        imagen_obj = Imagen.objects.get(id=imagen_id)
    except Imagen.DoesNotExist:
        return HttpResponse("Imagen no encontrada", status=404)

    if imagen_obj.url_gcp:
        return JsonResponse({'url_gcp': imagen_obj.url_gcp})
    else:
        return HttpResponse("La imagen no está disponible en GCS", status=404)


def health_check(request):
    return HttpResponse('ok')
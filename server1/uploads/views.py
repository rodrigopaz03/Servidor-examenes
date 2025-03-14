import json
from concurrent.futures import ThreadPoolExecutor
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from google.cloud import storage
from .models import Imagen

executor = ThreadPoolExecutor(max_workers=16)

def upload_to_gcs(file_data, destination_blob_name, content_type):
    client = storage.Client()
    bucket_name = 'arquisoft-bucket'
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_string(file_data, content_type=content_type)
    blob.make_public()

    return blob.public_url

def process_image(imagen_id, titulo, archivo_data, content_type):
    try:
        destination_blob_name = f'imagenes/{imagen_id}_{titulo}'
        public_url = upload_to_gcs(archivo_data, destination_blob_name, content_type)

        imagen_obj = Imagen.objects.get(pk=imagen_id)
        imagen_obj.url_gcp = public_url
        imagen_obj.save()

    except Exception as e:
        print(f"Error al subir la imagen {imagen_id} a GCS: {e}")

@csrf_exempt
def upload_imagen(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    archivo = request.FILES.get('imagen')

    if not archivo:
        return JsonResponse({'error': 'No se recibió ningún archivo'}, status=400)

    titulo = archivo.name
    content_type = archivo.content_type
    archivo_data = archivo.read()

    imagen_obj = Imagen.objects.create(titulo=titulo, content_type=content_type)

    executor.submit(process_image, imagen_obj.id, titulo, archivo_data, content_type)

    return JsonResponse({
        'msg': 'Imagen recibida correctamente.',
        'id_imagen': imagen_obj.id,
        'nota': 'La imagen se está subiendo a Google Cloud Storage en segundo plano.'
    }, status=202)

def serve_imagen(request, imagen_id):
    try:
        imagen_obj = Imagen.objects.get(id=imagen_id)
    except Imagen.DoesNotExist:
        return HttpResponse("Imagen no encontrada", status=404)

    if imagen_obj.url_gcp:
        return JsonResponse({'url_gcp': imagen_obj.url_gcp})
    else:
        return JsonResponse({'msg': 'La imagen aún se está subiendo a Google Cloud Storage.'}, status=202)

def health_check(request):
    return HttpResponse('ok')

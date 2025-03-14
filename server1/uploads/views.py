from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from google.cloud import storage
from .models import Imagen
import uuid

# Define estas variables en tu configuración segura (settings.py o variables de entorno)
BUCKET_NAME = 'arquisoft-bucket'

def subir_a_gcs(file, file_name, content_type):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_name)

    blob.upload_from_file(file, content_type=content_type)
    blob.make_public()  # si deseas URL pública inmediatamente

    return blob.public_url

@csrf_exempt  
def upload_imagen(request):
    if request.method == 'POST':
        archivo = request.FILES.get('imagen')
        if archivo:
            if not archivo.content_type.startswith('image/'):
                return JsonResponse({'error': 'El archivo subido no es una imagen'}, status=400)
            
            # Genera un nombre único para evitar colisiones
            nombre_archivo_gcs = f"{uuid.uuid4()}_{archivo.name}"

            # Sube el archivo a GCS directamente desde memoria
            imagen_url = subir_a_gcs(archivo.file, nombre_archivo_gcs, archivo.content_type)

            # Guarda la URL en la base de datos
            imagen_obj = Imagen.objects.create(
                titulo=archivo.name,
                imagen_url=imagen_url,
            )

            return JsonResponse({
                'msg': 'Imagen almacenada correctamente en GCS y URL guardada en base de datos',
                'id': imagen_obj.id,
                'imagen_url': imagen_url
            }, status=201)
        else:
            return JsonResponse({'error': 'No se recibió ningún archivo'}, status=400)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def serve_imagen(request, imagen_id):
    try:
        imagen_obj = Imagen.objects.get(id=imagen_id)
    except Imagen.DoesNotExist:
        return HttpResponse("Imagen no encontrada", status=404)

    # Redirige a la URL en GCS
    return JsonResponse({
        'imagen_url': imagen_obj.imagen_url
    })

def health_check(request):
    return HttpResponse('ok')

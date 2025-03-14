import json
import threading
from concurrent.futures import ThreadPoolExecutor
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from .models import Imagen, ImagenChunk

executor = ThreadPoolExecutor(max_workers=16)

@csrf_exempt
def upload_imagen(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        chunk_index = int(request.POST.get('chunk_index', 0))
        total_chunks = int(request.POST.get('total_chunks', 1))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'chunk_index y total_chunks deben ser enteros'}, status=400)

    imagen_id = request.POST.get('imagen_id')  # Sólo en chunks posteriores
    titulo = request.POST.get('titulo', 'Imagen sin título')
    content_type = request.POST.get('content_type', 'application/octet-stream')

    chunk_file = request.FILES.get('imagen')
    if not chunk_file:
        return JsonResponse({'error': 'No se recibió ningún archivo en FILES'}, status=400)

    chunk_data = chunk_file.read()

    # Función que hace el trabajo real en segundo plano.
    def process_chunk(imagen_id, titulo, content_type, chunk_data, chunk_index, total_chunks):
        try:
            # Si es el primer chunk, crea el registro de la imagen
            if not imagen_id:
                imagen_obj = Imagen.objects.create(titulo=titulo, content_type=content_type)
                imagen_id_local = imagen_obj.id
            else:
                imagen_obj = Imagen.objects.get(id=imagen_id)
                imagen_id_local = imagen_obj.id

            # Guardamos este chunk en la BD
            ImagenChunk.objects.create(
                imagen=imagen_obj,
                chunk_index=chunk_index,
                chunk_data=chunk_data
            )

            # Si este chunk es el último en llegar (o en total ya tenemos todos), ensamblamos
            if imagen_obj.chunks.count() == total_chunks:
                with transaction.atomic():
                    chunks = imagen_obj.chunks.order_by('chunk_index')
                    full_data = b''.join(chunk.chunk_data for chunk in chunks)
                    imagen_obj.imagen_binaria = full_data
                    imagen_obj.ensamblada = True
                    imagen_obj.save()
                    # Limpieza opcional de los chunks
                    imagen_obj.chunks.all().delete()

        except Imagen.DoesNotExist:
            # Podrías registrar en logs o manejar el error
            pass
        except Exception as e:
            # Manejo general de errores en logs, etc.
            pass

    # Disparamos la tarea en segundo plano, sin bloquear la respuesta.
    executor.submit(
        process_chunk,
        imagen_id,
        titulo,
        content_type,
        chunk_data,
        chunk_index,
        total_chunks
    )

  
    return JsonResponse({
        'msg': 'Chunk recibido y en proceso',
        'nota': (
            'El servidor procesará el chunk y ensamblará la imagen en '
            'segundo plano; no hay confirmación inmediata de escritura final.'
        ),
        'imagen_id': imagen_id or 'pendiente'
    }, status=202)

def serve_imagen(request, imagen_id):
    try:
        imagen_obj = Imagen.objects.get(id=imagen_id)
    except Imagen.DoesNotExist:
        return HttpResponse("Imagen no encontrada", status=404)

    return HttpResponse(imagen_obj.imagen_binaria, content_type=imagen_obj.content_type)

def health_check(request):
    return HttpResponse('ok')

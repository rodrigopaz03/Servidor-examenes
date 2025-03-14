import json
import threading
from concurrent.futures import ThreadPoolExecutor
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from .models import Imagen, ImagenChunk

executor = ThreadPoolExecutor(max_workers=8000)  

@csrf_exempt
def upload_imagen(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        chunk_index = int(request.POST.get('chunk_index', 0))
        total_chunks = int(request.POST.get('total_chunks', 1))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'chunk_index y total_chunks deben ser enteros'}, status=400)

    imagen_id = request.POST.get('imagen_id')  # Solo en chunks posteriores
    titulo = request.POST.get('titulo', 'Imagen sin título')
    content_type = request.POST.get('content_type', 'application/octet-stream')

    chunk_file = request.FILES.get('imagen')
    if not chunk_file:
        return JsonResponse({'error': 'No se recibió ningún archivo en FILES'}, status=400)

    chunk_data = chunk_file.read()

    def process_chunk():
        """Procesa y almacena el chunk en la base de datos."""
        # Si es el primer chunk, crea el registro de la imagen
        if not imagen_id:
            imagen_obj = Imagen.objects.create(titulo=titulo, content_type=content_type)
            imagen_id_local = imagen_obj.id
        else:
            try:
                imagen_obj = Imagen.objects.get(id=imagen_id)
                imagen_id_local = imagen_obj.id
            except Imagen.DoesNotExist:
                return JsonResponse({'error': 'Imagen no encontrada'}, status=404)

        # Guardar chunk en la base de datos
        ImagenChunk.objects.create(imagen=imagen_obj, chunk_index=chunk_index, chunk_data=chunk_data)

        # Comprobamos si ya han llegado todos los chunks para ensamblar la imagen
        if imagen_obj.chunks.count() == total_chunks:
            with transaction.atomic():
                chunks = imagen_obj.chunks.order_by('chunk_index')
                full_data = b''.join(chunk.chunk_data for chunk in chunks)
                imagen_obj.imagen_binaria = full_data
                imagen_obj.ensamblada = True
                imagen_obj.save()

                # Limpieza: Eliminar chunks después de ensamblar
                imagen_obj.chunks.all().delete()

        return JsonResponse({'imagen_id': imagen_id_local}, status=201)

    # Enviar tarea al ThreadPool para ejecución en paralelo
    future = executor.submit(process_chunk)
    return future.result()

def serve_imagen(request, imagen_id):
    try:
        imagen_obj = Imagen.objects.get(id=imagen_id)
    except Imagen.DoesNotExist:
        return HttpResponse("Imagen no encontrada", status=404)

    return HttpResponse(imagen_obj.imagen_binaria, content_type=imagen_obj.content_type)

def health_check(request):
    return HttpResponse('ok')

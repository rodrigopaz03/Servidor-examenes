from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Imagen, ImagenChunk

@csrf_exempt
def upload_imagen_chunk(request):
    """
    Vista para subir la imagen en pedazos (chunks).
    
    Se esperan los siguientes parámetros en POST:
      - chunk_index: Índice (0 basado) del pedazo actual.
      - total_chunks: Total de pedazos que se enviarán.
      - (opcional) imagen_id: Si se trata de un chunk subsecuente, el ID de la imagen previamente creada.
      - titulo: (opcional) Título de la imagen (solo en el primer chunk).
      - content_type: (opcional) Tipo de contenido (solo en el primer chunk).
      - El archivo del chunk se envía en FILES con la clave "imagen".
    """
    if request.method == 'POST':
        try:
            chunk_index = int(request.POST.get('chunk_index', 0))
            total_chunks = int(request.POST.get('total_chunks', 1))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Parámetros chunk_index y total_chunks deben ser enteros'}, status=400)
        
        imagen_id = request.POST.get('imagen_id')
        titulo = request.POST.get('titulo', 'Imagen sin título')
        content_type = request.POST.get('content_type', 'application/octet-stream')
        
        chunk_file = request.FILES.get('imagen')
        if not chunk_file:
            return JsonResponse({'error': 'No se recibió ningún archivo en FILES'}, status=400)
        
        chunk_data = chunk_file.read()

        # Si se envía imagen_id, se asume que ya existe la imagen
        if imagen_id:
            try:
                imagen_obj = Imagen.objects.get(id=imagen_id)
            except Imagen.DoesNotExist:
                return JsonResponse({'error': 'Imagen no encontrada'}, status=404)
        else:
            # Para el primer chunk, creamos la imagen base
            imagen_obj = Imagen.objects.create(titulo=titulo, content_type=content_type)

        # Guardar el chunk actual
        ImagenChunk.objects.create(imagen=imagen_obj, chunk_index=chunk_index, chunk_data=chunk_data)

        # Si se ha recibido el último chunk, reensamblamos la imagen
        if chunk_index == total_chunks - 1:
            # Obtener todos los chunks en orden y concatenar sus datos
            chunks = imagen_obj.chunks.order_by('chunk_index')
            full_data = b''.join(chunk.chunk_data for chunk in chunks)
            imagen_obj.imagen_binaria = full_data
            imagen_obj.ensamblada = True
            imagen_obj.save()

            # (Opcional) Eliminar los chunks después de ensamblar
            imagen_obj.chunks.all().delete()

        return JsonResponse({'imagen_id': imagen_obj.id}, status=201)
    return JsonResponse({'error': 'Método no permitido'}, status=405)


def health_check(request):
    return HttpResponse("ok")
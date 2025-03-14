from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Imagen

@csrf_exempt  
def upload_imagen(request):
    if request.method == 'POST':
        archivo = request.FILES.get('imagen')
        if archivo:
            if not archivo.content_type.startswith('image/'):
                return JsonResponse({'error': 'El archivo subido no es una imagen'}, status=400)
            contenido = archivo.read()
            imagen_obj = Imagen.objects.create(
                titulo=archivo.name,
                imagen_binaria=contenido,
                content_type=archivo.content_type,
                ensamblada=False  
            )
            return JsonResponse({'msg': 'Imagen almacenada en la base de datos', 'id': imagen_obj.id}, status=201)
        else:
            return JsonResponse({'error': 'No se recibió ningún archivo'}, status=400)
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@csrf_exempt  
def serve_imagen(request, imagen_id):
    try:
        imagen_obj = Imagen.objects.get(id=imagen_id)
    except Imagen.DoesNotExist:
        return HttpResponse("Imagen no encontrada", status=404)
    
    return HttpResponse(imagen_obj.imagen_binaria, content_type=imagen_obj.content_type)

@csrf_exempt  
def health_check(request):
    return HttpResponse('ok')

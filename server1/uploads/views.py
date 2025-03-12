from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Imagen

@csrf_exempt  # En producción, configura CSRF adecuadamente
def upload_imagen(request):
    if request.method == 'POST':
        archivo = request.FILES.get('imagen')
        if archivo:
            # Puedes opcionalmente asignar un título desde POST o usar el nombre del archivo
            titulo = request.POST.get('titulo', archivo.name)
            imagen_obj = Imagen.objects.create(
                titulo=titulo,
                imagen=archivo
            )
            return JsonResponse({'msg': 'Imagen guardada correctamente', 'id': imagen_obj.id}, status=201)
        else:
            return JsonResponse({'error': 'No se recibió ningún archivo'}, status=400)
    return JsonResponse({'error': 'Método no permitido'}, status=405)

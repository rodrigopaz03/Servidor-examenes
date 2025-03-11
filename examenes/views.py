from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Server1Archivo

@csrf_exempt
def server1_archivo(request):
    if request.method == 'POST':
        archivo = request.FILES.get('archivo')
        if archivo:
            contenido = archivo.read() 
            objeto = Server1Archivo.objects.create(
                nombre=archivo.name,
                archivo_binario=contenido
            )
            return JsonResponse({'msg': 'Guardado en la BD (server1)', 'id': objeto.id}, status=201)
        else:
            return JsonResponse({'error': 'No se recibió el archivo'}, status=400)
    else:
        return JsonResponse({'error': 'Método no permitido'}, status=405)

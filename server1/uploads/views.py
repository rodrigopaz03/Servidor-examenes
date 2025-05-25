from django.http import HttpResponseNotFound, JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import uuid
import os

# uploads/views.py
import base64
import datetime
import requests
from django.http     import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf    import settings
from .firestone_client import db

@csrf_exempt
def upload_imagen(request):
    archivo = request.FILES.get('imagen')
    paciente_id = request.POST.get('paciente_id')
    if not archivo or not paciente_id:
        return JsonResponse({"error":"imagen y paciente_id requeridos"}, status=400)

    resp = requests.get(f"{settings.SERVER2_URL}pacientes/{paciente_id}/")
    if resp.status_code != 200:
        return JsonResponse({"error":"Paciente no válido"}, status=400)

    contenido = archivo.read()
    doc_ref = db.collection('imagenes').document()  # ID auto
    doc_ref.set({
        "filename":     archivo.name,
        "content_type": archivo.content_type,
        "patient_id":   paciente_id,
        "uploaded_at":  datetime.datetime.utcnow().isoformat()+"Z",
        "bytes":        base64.b64encode(contenido).decode('ascii')
    })

    return JsonResponse({
        "id":  doc_ref.id,
        "url": f"/imagenes/{doc_ref.id}/"
    }, status=201)

def imagenes_por_paciente(request, paciente_id):

    docs = db.collection('imagenes').where('patient_id','==',paciente_id).stream()
    resultados = []
    for doc in docs:
        d = doc.to_dict()
        resultados.append({
            "id":          doc.id,
            "filename":    d["filename"],
            "content_type":d["content_type"],
            "uploaded_at": d["uploaded_at"],
        })
    return JsonResponse(resultados, safe=False)

@csrf_exempt
def serve_imagen(request, imagen_id):
    """
    Busca en Firestore el documento con ID = imagen_id
    y devuelve su URL pública en JSON.
    """
    doc_ref = db.collection('imagenes').document(imagen_id)
    doc = doc_ref.get()
    if not doc.exists:
        return HttpResponseNotFound("Imagen no encontrada")

    data = doc.to_dict()
    # Asumo que guardas la URL pública en el campo 'url'
    return JsonResponse({'url': data.get('url')})


@csrf_exempt
def health_check(request):
    return HttpResponse('ok')

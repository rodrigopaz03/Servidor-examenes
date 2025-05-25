from django.http import JsonResponse, HttpResponse
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
from .firestore_client import db

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
def health_check(request):
    return HttpResponse('ok')

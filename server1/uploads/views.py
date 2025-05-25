import json
import datetime

from django.http import JsonResponse, HttpResponseNotFound, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from google.cloud import firestore

# Cliente Firestore (usa tu proyecto y base de datos)
db = firestore.Client(
    project="exalted-booster-454620-j9",
    database="db-imagenes"
)


@csrf_exempt
def init_upload(request):
    """
    Crea el documento padre en Firestore con la metadata inicial:
    paciente_id, filename, content_type, chunks_count, uploaded_at.
    Devuelve {"doc_id": ...}
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Método no permitido")

    try:
        payload = json.loads(request.body)
        paciente_id  = payload['paciente_id']
        filename     = payload['filename']
        content_type = payload['content_type']
        chunks_count = int(payload['chunks_count'])
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return HttpResponseBadRequest(f"JSON inválido o falta campo: {e}")

    # Crear documento con ID aleatorio
    doc_ref = db.collection('imagenes').document()
    doc_ref.set({
        'patient_id':   paciente_id,
        'filename':     filename,
        'content_type': content_type,
        'chunks_count': chunks_count,
        'uploaded_at':  datetime.datetime.utcnow().isoformat() + 'Z',
    })

    return JsonResponse({'doc_id': doc_ref.id})


@csrf_exempt
def upload_chunk(request):
    """
    Recibe cada trozo:
      { doc_id, chunk_index, data }
    y lo almacena en la subcolección "chunks" del documento padre.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Método no permitido")

    try:
        payload     = json.loads(request.body)
        doc_id      = payload['doc_id']
        idx         = int(payload['chunk_index'])
        b64_data    = payload['data']
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return HttpResponseBadRequest(f"JSON inválido o falta campo: {e}")

    parent = db.collection('imagenes').document(doc_id)
    # Opcional: podrías verificar que parent.get().exists
    chunk_ref = parent.collection('chunks').document(f"{idx:04d}")
    chunk_ref.set({'data': b64_data})

    return JsonResponse({'status': 'ok', 'chunk_index': idx})


@csrf_exempt
def imagenes_por_paciente(request, paciente_id):
    """
    Devuelve lista de imágenes para un paciente dado.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Método no permitido")

    docs = db.collection('imagenes') \
             .where('patient_id', '==', paciente_id) \
             .stream()

    resultados = []
    for doc in docs:
        d = doc.to_dict()
        resultados.append({
            'id':           doc.id,
            'filename':     d.get('filename'),
            'content_type': d.get('content_type'),
            'uploaded_at':  d.get('uploaded_at'),
        })

    return JsonResponse(resultados, safe=False)


@csrf_exempt
def serve_imagen(request, imagen_id):
    """
    Recupera la URL pública (campo 'url') del documento imagen.
    """
    if request.method != 'GET':
        return HttpResponseBadRequest("Método no permitido")

    doc_ref = db.collection('imagenes').document(imagen_id)
    doc = doc_ref.get()
    if not doc.exists:
        return HttpResponseNotFound('Imagen no encontrada')

    data = doc.to_dict()
    return JsonResponse({'url': data.get('url')})


@csrf_exempt
def health_check(request):
    return HttpResponse('ok')

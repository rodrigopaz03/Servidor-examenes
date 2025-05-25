from django.http import HttpResponseNotFound, JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import uuid
import os
from io import BytesIO
from PIL import Image
from google.cloud import firestore
import base64
import datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


db = firestore.Client(project="exalted-booster-454620-j9", database="db-imagenes")

@csrf_exempt
def upload_imagen(request, paciente_id):
    """
    Recibe un archivo en multipart/form-data (campo 'file'),
    aplica thumbnail, codifica en base64 y fragmenta en chunks,
    guarda metadata y chunks en Firestore de forma concurrente.
    """
    try:
        archivo = request.FILES['file']
    except KeyError:
        return JsonResponse({'error': 'Falta el campo file'}, status=400)

    # Procesar imagen: thumbnail + compresión JPEG
    img = Image.open(archivo)
    img.thumbnail((1024, 1024))
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=75)
    contenido = buf.getvalue()

    # Codificar en base64 y fragmentar
    b64 = base64.b64encode(contenido).decode('ascii')
    CHUNK_SIZE = 200_000
    chunks = [b64[i:i+CHUNK_SIZE] for i in range(0, len(b64), CHUNK_SIZE)]

    # Crear documento padre con metadata
    doc_ref = db.collection('imagenes').document()
    doc_ref.set({
        'filename': archivo.name,
        'content_type': archivo.content_type,
        'patient_id': paciente_id,
        'uploaded_at': datetime.datetime.utcnow().isoformat() + 'Z',
        'chunks_count': len(chunks),
    })

    # Subida concurrente de chunks
    def _upload_chunk(idx, data):
        cr = doc_ref.collection('chunks').document(f"{idx:04d}")
        cr.set({'data': data})

    # Ajusta max_workers según tu cuota de Firestore
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_upload_chunk, idx, chunk)
                   for idx, chunk in enumerate(chunks)]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                # Aquí podrías loguear o manejar reintentos
                print(f"Error subiendo chunk: {e}")

    return JsonResponse({'doc_id': doc_ref.id, 'chunks': len(chunks)})

@csrf_exempt
def imagenes_por_paciente(request, paciente_id):
    """
    Devuelve la lista de imágenes subidas por paciente_id.
    """
    docs = db.collection('imagenes').where('patient_id', '==', paciente_id).stream()
    resultados = []
    for doc in docs:
        d = doc.to_dict()
        resultados.append({
            'id': doc.id,
            'filename': d.get('filename'),
            'content_type': d.get('content_type'),
            'uploaded_at': d.get('uploaded_at'),
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
        return HttpResponseNotFound('Imagen no encontrada')

    data = doc.to_dict()
    # Asumimos que guardas la URL pública en el campo 'url'
    return JsonResponse({'url': data.get('url')})

@csrf_exempt
def health_check(request):
    return HttpResponse('ok')

import json
import datetime

from django.http import (
    JsonResponse, HttpResponseNotFound,
    HttpResponseBadRequest, HttpResponse
)
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from google.cloud import firestore
import base64
from io import BytesIO
from PIL import Image

db = firestore.Client(
    project="exalted-booster-454620-j9",
    database="db-imagenes"
)


def _cors_preflight_response():
    """Devuelve un HttpResponse con headers CORS para preflight OPTIONS."""
    res = HttpResponse()
    res["Access-Control-Allow-Origin"] = "*"
    res["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    res["Access-Control-Allow-Headers"] = "Content-Type"
    return res


@csrf_exempt
def init_upload(request):
    """
    Crea el documento padre en Firestore con la metadata inicial.
    Soporta POST y responde OPTIONS para CORS.
    """
    if request.method == "OPTIONS":
        return _cors_preflight_response()

    if request.method != "POST":
        return HttpResponseBadRequest("Método no permitido")

    try:
        payload = json.loads(request.body)
        paciente_id  = payload["paciente_id"]
        filename     = payload["filename"]
        content_type = payload["content_type"]
        chunks_count = int(payload["chunks_count"])
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return HttpResponseBadRequest(f"JSON inválido o falta campo: {e}")

    # Crear documento con ID aleatorio
    doc_ref = db.collection("imagenes").document()
    doc_ref.set({
        "patient_id":   paciente_id,
        "filename":     filename,
        "content_type": content_type,
        "chunks_count": chunks_count,
        "uploaded_at":  datetime.datetime.utcnow().isoformat() + "Z",
    })

    res = JsonResponse({"doc_id": doc_ref.id})
    res["Access-Control-Allow-Origin"] = "*"
    return res


@csrf_exempt
def upload_chunk(request):
    """
    Recibe cada trozo y lo almacena:
      { doc_id, chunk_index, data }
    Soporta POST y responde OPTIONS para CORS.
    """
    if request.method == "OPTIONS":
        return _cors_preflight_response()

    if request.method != "POST":
        return HttpResponseBadRequest("Método no permitido")

    try:
        payload  = json.loads(request.body)
        doc_id   = payload["doc_id"]
        idx      = int(payload["chunk_index"])
        b64_data = payload["data"]
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return HttpResponseBadRequest(f"JSON inválido o falta campo: {e}")

    parent    = db.collection("imagenes").document(doc_id)
    chunk_ref = parent.collection("chunks").document(f"{idx:04d}")
    chunk_ref.set({"data": b64_data})

    res = JsonResponse({"status": "ok", "chunk_index": idx})
    res["Access-Control-Allow-Origin"] = "*"
    return res


@csrf_exempt
def imagenes_por_paciente(request, paciente_id):
    """
    Devuelve lista de imágenes para un paciente dado.
    """
    if request.method != "GET":
        return HttpResponseBadRequest("Método no permitido")

    docs = (
        db.collection("imagenes")
          .where("patient_id", "==", paciente_id)
          .stream()
    )

    resultados = []
    for doc in docs:
        d = doc.to_dict()
        resultados.append({
            "id":           doc.id,
            "filename":     d.get("filename"),
            "content_type": d.get("content_type"),
            "uploaded_at":  d.get("uploaded_at"),
        })

    res = JsonResponse(resultados, safe=False)
    res["Access-Control-Allow-Origin"] = "*"
    return res

def download_image(doc_id):
    """
    Lee todos los chunks de la imagen con ID = doc_id, los concatena,
    los decodifica de Base64 y devuelve un objeto BytesIO listo
    para, por ejemplo, enviar en una respuesta HTTP o abrir con PIL.
    """
    doc_ref = db.collection('imagenes').document(doc_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise ValueError(f"Imagen {doc_id} no encontrada")

    meta = doc.to_dict()
    chunks_count = meta.get('chunks_count', 0)
    if chunks_count == 0:
        raise ValueError(f"Ningún chunk registrado para la imagen {doc_id}")

    partes = []
    for idx in range(chunks_count):
        chunk_ref = doc_ref.collection('chunks').document(f"{idx:04d}")
        chunk_doc = chunk_ref.get()
        if not chunk_doc.exists:
            raise ValueError(f"Falta el chunk {idx:04d} para la imagen {doc_id}")
        partes.append(chunk_doc.to_dict()['data'])

    todo_b64 = ''.join(partes)
    imagen_bytes = base64.b64decode(todo_b64)

    return BytesIO(imagen_bytes)


@csrf_exempt
def serve_imagen(request, imagen_id):
    """
    Recupera la URL pública (campo 'url') del documento imagen.
    """
    if request.method != "GET":
        return HttpResponseBadRequest("Método no permitido")

    doc_ref = db.collection("imagenes").document(imagen_id)
    doc     = doc_ref.get()
    if not doc.exists:
        return HttpResponseNotFound("Imagen no encontrada")

    data = doc.to_dict()
    res  = JsonResponse({"url": data.get("url")})
    res["Access-Control-Allow-Origin"] = "*"
    return res


@csrf_exempt
def health_check(request):
    return HttpResponse("ok")


@csrf_exempt
@require_http_methods(["OPTIONS", "POST"])
def init_upload(request):
    # 1) manejamos el preflight OPTIONS
    if request.method == "OPTIONS":
        res = HttpResponse()
        res["Access-Control-Allow-Origin"]  = "*"
        res["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        res["Access-Control-Allow-Headers"] = "Content-Type, X-CSRFToken"
        return res

    import json
    payload = json.loads(request.body.decode())
    paciente_id   = payload.get("paciente_id")
    filename      = payload.get("filename")
    content_type  = payload.get("content_type")
    chunks_count  = payload.get("chunks_count")

    # crea el doc padre
    doc_ref = db.collection("imagenes").document()
    doc_ref.set({
        "filename":     filename,
        "content_type": content_type,
        "patient_id":   paciente_id,
        "uploaded_at":  datetime.datetime.utcnow().isoformat() + "Z",
        "chunks_count": chunks_count,
    })

    res = JsonResponse({"doc_id": doc_ref.id})
    res["Access-Control-Allow-Origin"] = "*"
    return res

@csrf_exempt
@require_http_methods(["OPTIONS", "POST"])
def upload_chunk(request):
    if request.method == "OPTIONS":
        res = HttpResponse()
        res["Access-Control-Allow-Origin"]  = "*"
        res["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        res["Access-Control-Allow-Headers"] = "Content-Type, X-CSRFToken"
        return res

    import json
    payload    = json.loads(request.body.decode())
    doc_id     = payload.get("doc_id")
    idx        = payload.get("chunk_index")
    data       = payload.get("data")

    doc_ref = db.collection("imagenes").document(doc_id)
    chunk_ref = doc_ref.collection("chunks").document(f"{int(idx):04d}")
    chunk_ref.set({"data": data})

    res = JsonResponse({"status": "ok"})
    res["Access-Control-Allow-Origin"] = "*"
    return res
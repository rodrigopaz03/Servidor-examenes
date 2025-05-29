import json
import datetime
import base64
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from google.cloud import firestore

# Inicializamos cliente Firestore
db = firestore.Client(
    project="exalted-booster-454620-j9",
    database="db-imagenes"
)

def _cors_preflight_response():
    """Devuelve un HttpResponse con headers CORS para preflight OPTIONS."""
    res = HttpResponse()
    res["Access-Control-Allow-Origin"] = "*"
    res["Access-Control-Allow-Methods"] = "POST, OPTIONS, GET"
    res["Access-Control-Allow-Headers"] = "Content-Type, X-CSRFToken"
    return res

@csrf_exempt
@require_http_methods(["OPTIONS", "POST"])
def init_upload(request):
    """
    Crea el documento padre en Firestore con la metadata inicial.
    Soporta preflight OPTIONS y POST.
    """
    if request.method == "OPTIONS":
        return _cors_preflight_response()

    try:
        payload = json.loads(request.body.decode())
        paciente_id = payload["paciente_id"]
        filename = payload["filename"]
        content_type = payload["content_type"]
        chunks_count = int(payload["chunks_count"])
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return HttpResponseBadRequest(f"JSON inválido o falta campo: {e}")

    # Creamos doc con ID aleatorio
    doc_ref = db.collection("imagenes").document()
    doc_ref.set({
        "patient_id":  paciente_id,
        "filename":    filename,
        "content_type": content_type,
        "chunks_count": chunks_count,
        "uploaded_at": datetime.datetime.utcnow().isoformat() + "Z",
    })

    res = JsonResponse({"doc_id": doc_ref.id})
    res["Access-Control-Allow-Origin"] = "*"
    return res

@csrf_exempt
@require_http_methods(["OPTIONS", "POST"])
def upload_chunk(request):
    """
    Recibe cada chunk y lo almacena en Firestore.
    Soporta preflight OPTIONS y POST.
    """
    if request.method == "OPTIONS":
        return _cors_preflight_response()

    try:
        payload = json.loads(request.body.decode())
        doc_id = payload["doc_id"]
        idx = int(payload["chunk_index"])
        data = payload["data"]
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return HttpResponseBadRequest(f"JSON inválido o falta campo: {e}")

    # Guardamos chunk en subcolección "chunks"
    db.collection("imagenes").document(doc_id) \
      .collection("chunks").document(f"{idx:04d}") \
      .set({"data": data})

    res = JsonResponse({"status": "ok", "chunk_index": idx})
    res["Access-Control-Allow-Origin"] = "*"
    return res

@csrf_exempt
@require_http_methods(["GET"])
def imagenes_por_paciente(request, paciente_id):
    """
    Devuelve lista de imágenes de un paciente.
    """
    docs = db.collection("imagenes") \
             .where("patient_id", "==", paciente_id) \
             .stream()

    resultados = []
    for doc in docs:
        d = doc.to_dict()
        resultados.append({
            "id": doc.id,
            "filename": d.get("filename"),
            "content_type": d.get("content_type"),
            "uploaded_at": d.get("uploaded_at"),
        })

    res = JsonResponse(resultados, safe=False)
    res["Access-Control-Allow-Origin"] = "*"
    return res


@csrf_exempt
@require_http_methods(["GET"])
def serve_imagen(request, imagen_id):
    """
    Recupera la URL pública (campo 'url') del documento imagen.
    """
    doc_ref = db.collection("imagenes").document(imagen_id)
    doc = doc_ref.get()
    if not doc.exists:
        return HttpResponseNotFound("Imagen no encontrada")

    url = doc.to_dict().get("url")
    if not url:
        return HttpResponseNotFound("URL de imagen no encontrado")

    res = JsonResponse({"url": url})
    res["Access-Control-Allow-Origin"] = "*"
    return res

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Endpoint de verificación de salud.
    """
    res = HttpResponse("ok")
    res["Access-Control-Allow-Origin"] = "*"
    return res


@csrf_exempt
@require_http_methods(["GET"])
def download_imagen(request, imagen_id):
    # 1) leo metadata y chunks_count de Firestore
    doc_ref = db.collection("imagenes").document(imagen_id)
    doc = doc_ref.get()
    if not doc.exists:
        return HttpResponseNotFound("Imagen no encontrada")
    meta = doc.to_dict()
    count = int(meta["chunks_count"])
    content_type = meta["content_type"]
    filename = meta["filename"]

    # 2) concateno chunks base64
    partes = []
    for i in range(count):
        c = doc_ref.collection("chunks").document(f"{i:04d}").get()
        partes.append(c.to_dict()["data"])
    data = base64.b64decode("".join(partes))

    # 3) devuelvo el binario con CORS permitido
    resp = HttpResponse(data, content_type=content_type)
    resp["Access-Control-Allow-Origin"] = "*"
    resp["Content-Disposition"] = f'inline; filename="{filename}"'
    return resp

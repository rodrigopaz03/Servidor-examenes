from django.db import models


class Imagen(models.Model):
    titulo = models.CharField(max_length=100, blank=True)
    imagen_binaria = models.BinaryField()  # Guarda el contenido binario
    content_type = models.CharField(max_length=50, blank=True, null=True)  # Opcional: tipo de archivo (e.g., "image/jpeg")
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo or f"Imagen {self.pk}"

from django.db import models

class Imagen(models.Model):
    titulo = models.CharField(max_length=100, blank=True)
    url_gcp = models.URLField(null=True, blank=True)
    content_type = models.CharField(max_length=50, blank=True, null=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo or f"Imagen {self.pk}"

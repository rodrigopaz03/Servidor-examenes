from django.db import models

class Imagen(models.Model):
    titulo = models.CharField(max_length=100, blank=True)
    # Se usará este campo para almacenar la imagen completa, una vez que se hayan subido todos los pedazos
    imagen_binaria = models.BinaryField(null=True, blank=True)
    content_type = models.CharField(max_length=50, blank=True, null=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    ensamblada = models.BooleanField(default=False)  # Indica si ya se reensambló

    def __str__(self):
        return self.titulo or f"Imagen {self.pk}"

class ImagenChunk(models.Model):
    imagen = models.ForeignKey(Imagen, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.IntegerField()  # Indica el orden del pedazo
    chunk_data = models.BinaryField()  # Datos binarios del pedazo

    class Meta:
        unique_together = ('imagen', 'chunk_index')
        ordering = ['chunk_index']

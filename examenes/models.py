from django.db import models

class Server1Archivo(models.Model):
    nombre = models.CharField(max_length=200)
    archivo_binario = models.BinaryField()

    def __str__(self):
        return self.nombre

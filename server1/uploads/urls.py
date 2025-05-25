"""
URL configuration for server1_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from . import views

urlpatterns = [
  
    path('init-upload/', views.init_upload, name='init_upload'),
    path('upload-chunk/', views.upload_chunk, name='upload_chunk'),
    path('pacientes/<str:paciente_id>/imagenes/', 
         views.imagenes_por_paciente, 
         name='imagenes_por_paciente'),
    path('imagenes/<str:imagen_id>/', 
         views.serve_imagen, 
         name='serve_imagen'),
    path('health/', views.health_check, name='health_check'),
]


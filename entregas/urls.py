from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("api/entregas/", views.lista, name="lista"),
    path("api/entregas/<int:pk>/", views.detalhe, name="detalhe"),
    path("entregas/<int:pk>/ficha/", views.ficha, name="ficha"),
    path("exportar/", views.exportar, name="exportar"),
    path("sw.js", views.service_worker, name="service-worker"),
]

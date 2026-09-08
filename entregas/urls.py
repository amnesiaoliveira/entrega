from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("entregadores/", views.cadastro_entregadores, name="cadastro-entregadores"),
    path("api/entregadores/", views.entregadores, name="entregadores"),
    path(
        "api/entregadores/<int:pk>/", views.editar_entregador, name="editar-entregador"
    ),
    path("api/entregas/", views.lista, name="lista"),
    path("api/clientes/por-cpf/", views.cliente_por_cpf, name="cliente-por-cpf"),
    path("api/entregas/<int:pk>/", views.detalhe, name="detalhe"),
    path("entregas/<int:pk>/ficha/", views.ficha, name="ficha"),
    path("exportar/", views.exportar, name="exportar"),
    path("roteiro/", views.roteiro, name="roteiro"),
    path("sw.js", views.service_worker, name="service-worker"),
]

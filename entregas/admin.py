from django.contrib import admin

from .models import Entrega, EventoEntrega


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "data", "status", "responsavel", "volumes")
    list_filter = ("status", "data")
    search_fields = ("nome", "cupom", "endereco", "responsavel")
    readonly_fields = [field.name for field in Entrega._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EventoEntrega)
class EventoEntregaAdmin(admin.ModelAdmin):
    list_display = ("entrega", "descricao", "usuario", "criado_em")
    readonly_fields = ("entrega", "descricao", "usuario", "criado_em")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

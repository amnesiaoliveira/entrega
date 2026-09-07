import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Entrega(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        EM_ROTA = "em_rota", "Em rota"
        ENTREGUE = "entregue", "Entregue"
        CANCELADA = "cancelada", "Cancelada"

    nome = models.CharField("nome completo", max_length=150)
    endereco = models.CharField("endereço completo", max_length=500)
    telefone = models.CharField("telefone", max_length=30)
    cupom = models.CharField("número do cupom", max_length=50)
    volumes = models.PositiveIntegerField(
        "quantidade de volumes", default=1, validators=[MinValueValidator(1)]
    )
    data = models.DateField(
        "data da entrega", default=timezone.localdate, db_index=True
    )
    horario = models.TimeField("horário previsto", null=True, blank=True)
    responsavel = models.CharField("entregador", max_length=100, blank=True)
    observacoes = models.TextField("observações", max_length=1000, blank=True)
    status = models.CharField(
        max_length=12, choices=Status, default=Status.PENDENTE, db_index=True
    )
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    entregue_em = models.DateTimeField(null=True, blank=True)
    versao = models.PositiveIntegerField(default=1)
    requisicao = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(volumes__gte=1), name="entrega_volumes_positivos"
            ),
        ]

    @property
    def sequencia(self):
        return f"{self.pk:06d}"

    def __str__(self):
        return f"#{self.sequencia} · {self.nome}"


class EventoEntrega(models.Model):
    entrega = models.ForeignKey(
        Entrega, on_delete=models.CASCADE, related_name="eventos"
    )
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    descricao = models.CharField(max_length=160)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em", "-id"]

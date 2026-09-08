import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone


class ContadorDiario(models.Model):
    data = models.DateField(primary_key=True)
    ultimo_numero = models.PositiveBigIntegerField(default=0)


class Entregador(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    telefone = models.CharField(max_length=30, blank=True)
    ativo = models.BooleanField(default=True)
    versao = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["nome", "id"]
        verbose_name_plural = "entregadores"

    def __str__(self):
        return self.nome


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
    numero_diario = models.PositiveBigIntegerField("número diário", editable=False)
    horario = models.TimeField("horário previsto", null=True, blank=True)
    responsavel = models.CharField("entregador", max_length=100, blank=True)
    entregador = models.ForeignKey(
        Entregador,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="entregas",
    )
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
            models.UniqueConstraint(
                fields=["data", "numero_diario"], name="entrega_numero_unico_por_dia"
            ),
            models.CheckConstraint(
                condition=models.Q(volumes__gte=1), name="entrega_volumes_positivos"
            ),
        ]

    @property
    def sequencia(self):
        return f"{self.numero_diario:06d}"

    def save(self, *args, **kwargs):
        self.data = self._meta.get_field("data").to_python(self.data)
        # SQLite IMMEDIATE serializa a reserva e a gravação entre operadores.
        with transaction.atomic():
            update_fields = kwargs.get("update_fields")
            muda_data = False
            if not self._state.adding and (
                update_fields is None or "data" in update_fields
            ):
                anterior = (
                    type(self)
                    .objects.filter(pk=self.pk)
                    .values_list("data", flat=True)
                    .first()
                )
                muda_data = anterior is not None and anterior != self.data
            if self._state.adding or muda_data:
                contador, _ = ContadorDiario.objects.select_for_update().get_or_create(
                    data=self.data
                )
                contador.ultimo_numero += 1
                contador.save(update_fields=["ultimo_numero"])
                self.numero_diario = contador.ultimo_numero
                if update_fields is not None:
                    kwargs["update_fields"] = set(update_fields) | {"numero_diario"}
            super().save(*args, **kwargs)

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

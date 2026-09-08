import django.db.models.deletion
from django.db import migrations, models


def vincular_entregadores(apps, schema_editor):
    Entrega = apps.get_model("entregas", "Entrega")
    Entregador = apps.get_model("entregas", "Entregador")
    alias = schema_editor.connection.alias
    for nome in (
        Entrega.objects.using(alias)
        .exclude(responsavel="")
        .values_list("responsavel", flat=True)
        .distinct()
    ):
        if not nome.strip():
            continue
        entregador, _ = Entregador.objects.using(alias).get_or_create(nome=nome.strip())
        Entrega.objects.using(alias).filter(responsavel=nome).update(
            entregador_id=entregador.pk
        )


class Migration(migrations.Migration):
    dependencies = [("entregas", "0002_numeracao_diaria")]
    operations = [
        migrations.CreateModel(
            name="Entregador",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nome", models.CharField(max_length=100, unique=True)),
                ("telefone", models.CharField(max_length=30, blank=True)),
                ("ativo", models.BooleanField(default=True)),
                ("versao", models.PositiveIntegerField(default=1)),
            ],
            options={"ordering": ["nome", "id"], "verbose_name_plural": "entregadores"},
        ),
        migrations.AddField(
            model_name="entrega",
            name="entregador",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="entregas",
                to="entregas.entregador",
            ),
        ),
        migrations.RunPython(vincular_entregadores, migrations.RunPython.noop),
    ]

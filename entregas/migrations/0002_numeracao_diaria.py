from django.db import migrations, models


def preservar_numeros(apps, schema_editor):
    entrega = apps.get_model("entregas", "Entrega")
    entrega.objects.using(schema_editor.connection.alias).update(
        numero_diario=models.F("id")
    )
    contador = apps.get_model("entregas", "ContadorDiario")
    for grupo in (
        entrega.objects.using(schema_editor.connection.alias)
        .values("data")
        .annotate(ultimo=models.Max("numero_diario"))
    ):
        contador.objects.using(schema_editor.connection.alias).create(
            data=grupo["data"], ultimo_numero=grupo["ultimo"]
        )


class Migration(migrations.Migration):
    dependencies = [("entregas", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="ContadorDiario",
            fields=[
                ("data", models.DateField(primary_key=True, serialize=False)),
                ("ultimo_numero", models.PositiveBigIntegerField(default=0)),
            ],
        ),
        migrations.AddField(
            model_name="entrega",
            name="numero_diario",
            field=models.PositiveBigIntegerField(
                editable=False, null=True, verbose_name="número diário"
            ),
        ),
        migrations.RunPython(preservar_numeros, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="entrega",
            name="numero_diario",
            field=models.PositiveBigIntegerField(
                editable=False, verbose_name="número diário"
            ),
        ),
        migrations.AddConstraint(
            model_name="entrega",
            constraint=models.UniqueConstraint(
                fields=("data", "numero_diario"), name="entrega_numero_unico_por_dia"
            ),
        ),
    ]

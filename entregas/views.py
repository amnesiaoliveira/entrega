import csv
import json
import uuid
from datetime import date
from functools import wraps

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods

from .forms import EntregaForm
from .models import Entrega, EventoEntrega


def api_login(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"erro": "Sua sessão expirou. Entre novamente."}, status=401
            )
        return view(request, *args, **kwargs)

    return never_cache(wrapped)


def serializar(entrega):
    return {
        "id": entrega.pk,
        "sequencia": entrega.sequencia,
        **{
            campo: getattr(entrega, campo)
            for campo in [
                "nome",
                "endereco",
                "telefone",
                "cupom",
                "volumes",
                "responsavel",
                "observacoes",
                "status",
                "versao",
            ]
        },
        "data": entrega.data.isoformat(),
        "horario": entrega.horario.strftime("%H:%M") if entrega.horario else "",
        "atualizado_em": entrega.atualizado_em.isoformat(),
        "entregue_em": entrega.entregue_em.isoformat() if entrega.entregue_em else None,
    }


def selecionar(request):
    entregas = Entrega.objects.all()
    dia = request.GET.get("data", timezone.localdate().isoformat())
    if dia:
        entregas = entregas.filter(data=date.fromisoformat(dia))
    busca = request.GET.get("busca", "").strip()[:150]
    if busca:
        filtro = (
            Q(nome__icontains=busca)
            | Q(endereco__icontains=busca)
            | Q(cupom__icontains=busca)
            | Q(responsavel__icontains=busca)
        )
        if busca.lstrip("#").isdigit() and len(busca.lstrip("#")) < 18:
            filtro |= Q(pk=int(busca.lstrip("#")))
        entregas = entregas.filter(filtro)
    return entregas


@login_required
@never_cache
@ensure_csrf_cookie
def inicio(request):
    return render(
        request, "entregas/inicio.html", {"hoje": timezone.localdate().isoformat()}
    )


@require_http_methods(["GET", "POST"])
@api_login
def lista(request):
    if request.method == "GET":
        try:
            entregas = selecionar(request)
        except ValueError:
            return JsonResponse({"erro": "Data inválida."}, status=400)
        return JsonResponse(
            {
                "entregas": [serializar(item) for item in entregas],
                "consultado_em": timezone.now().isoformat(),
            }
        )
    try:
        dados = json.loads(request.body)
        if not isinstance(dados, dict):
            raise ValueError
        requisicao = uuid.UUID(str(dados.get("requisicao", "")))
    except ValueError, TypeError:
        return JsonResponse({"erro": "Dados de cadastro inválidos."}, status=400)
    with transaction.atomic():
        existente = Entrega.objects.filter(requisicao=requisicao).first()
        if existente:
            return JsonResponse({"entrega": serializar(existente)})
        form = EntregaForm(dados)
        if not form.is_valid():
            return JsonResponse({"erros": form.errors}, status=400)
        entrega = form.save(commit=False)
        entrega.criado_por = request.user
        entrega.requisicao = requisicao
        entrega.save()
        EventoEntrega.objects.create(
            entrega=entrega, usuario=request.user, descricao="Entrega cadastrada"
        )
    return JsonResponse({"entrega": serializar(entrega)}, status=201)


@require_http_methods(["GET", "PATCH"])
@api_login
def detalhe(request, pk):
    if request.method == "GET":
        entrega = get_object_or_404(Entrega, pk=pk)
        return JsonResponse(
            {
                "entrega": serializar(entrega),
                "eventos": [
                    {
                        "descricao": evento.descricao,
                        "usuario": evento.usuario.get_username(),
                        "criado_em": evento.criado_em.isoformat(),
                    }
                    for evento in entrega.eventos.select_related("usuario")
                ],
            }
        )
    try:
        dados = json.loads(request.body)
        if not isinstance(dados, dict):
            raise ValueError
    except ValueError, TypeError:
        return JsonResponse({"erro": "Dados inválidos."}, status=400)
    with transaction.atomic():
        entrega = get_object_or_404(Entrega.objects.select_for_update(), pk=pk)
        if dados.get("versao") != entrega.versao:
            return JsonResponse(
                {
                    "erro": "Esta entrega foi alterada. Atualize a lista antes de continuar."
                },
                status=409,
            )
        if entrega.status in (Entrega.Status.ENTREGUE, Entrega.Status.CANCELADA):
            return JsonResponse({"erro": "Esta entrega já foi finalizada."}, status=400)
        if "status" in dados:
            proximo = dados["status"]
            permitidos = {
                Entrega.Status.PENDENTE: [
                    Entrega.Status.EM_ROTA,
                    Entrega.Status.CANCELADA,
                ],
                Entrega.Status.EM_ROTA: [
                    Entrega.Status.ENTREGUE,
                    Entrega.Status.CANCELADA,
                ],
            }
            if proximo not in permitidos[entrega.status]:
                return JsonResponse({"erro": "Mudança de status inválida."}, status=400)
            if proximo == Entrega.Status.EM_ROTA and not entrega.responsavel:
                return JsonResponse(
                    {"erro": "Informe o entregador antes de iniciar a rota."},
                    status=400,
                )
            entrega.status = proximo
            if proximo == Entrega.Status.ENTREGUE:
                entrega.entregue_em = timezone.now()
            descricao = f"Status alterado para {entrega.get_status_display()}"
        else:
            form = EntregaForm(dados, instance=entrega)
            if not form.is_valid():
                return JsonResponse({"erros": form.errors}, status=400)
            entrega = form.save(commit=False)
            if entrega.status == Entrega.Status.EM_ROTA and not entrega.responsavel:
                return JsonResponse(
                    {"erro": "Uma entrega em rota precisa de entregador."}, status=400
                )
            descricao = "Dados da entrega atualizados"
        entrega.versao += 1
        entrega.save()
        EventoEntrega.objects.create(
            entrega=entrega, usuario=request.user, descricao=descricao
        )
    return JsonResponse({"entrega": serializar(entrega)})


@login_required
@never_cache
@require_GET
def ficha(request, pk):
    return render(
        request, "entregas/ficha.html", {"entrega": get_object_or_404(Entrega, pk=pk)}
    )


@api_login
@require_GET
def exportar(request):
    try:
        entregas = selecionar(request)
    except ValueError:
        return JsonResponse({"erro": "Data inválida."}, status=400)
    status = request.GET.get("status")
    if status:
        entregas = entregas.filter(status=status)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        'attachment; filename="entregas-super-baranda.csv"'
    )
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(
        [
            "Sequência",
            "Cliente",
            "Endereço",
            "Telefone",
            "Cupom",
            "Volumes",
            "Data",
            "Horário",
            "Entregador",
            "Status",
            "Observações",
        ]
    )
    for entrega in entregas:
        valores = [
            entrega.sequencia,
            entrega.nome,
            entrega.endereco,
            entrega.telefone,
            entrega.cupom,
            entrega.volumes,
            entrega.data,
            entrega.horario or "",
            entrega.responsavel,
            entrega.get_status_display(),
            entrega.observacoes,
        ]
        writer.writerow(
            [
                "'" + str(valor)
                if str(valor).lstrip().startswith(("=", "+", "-", "@"))
                or str(valor).startswith(("\t", "\r", "\n"))
                else valor
                for valor in valores
            ]
        )
    return response


@require_GET
def service_worker(request):
    response = FileResponse(
        (settings.BASE_DIR / "static" / "sw.js").open("rb"),
        content_type="application/javascript",
    )
    response["Cache-Control"] = "no-cache"
    response["Service-Worker-Allowed"] = "/"
    return response

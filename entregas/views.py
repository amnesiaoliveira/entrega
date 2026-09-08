import csv
import json
import re
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

from .forms import EntregadorForm, EntregaForm
from .models import Entrega, Entregador, EventoEntrega


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
        "entregador": entrega.entregador_id,
        **{
            campo: getattr(entrega, campo)
            for campo in [
                "nome",
                "cpf",
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


@require_http_methods(["POST"])
@api_login
def cliente_por_cpf(request):
    try:
        dados = json.loads(request.body)
        cpf = dados.get("cpf", "") if isinstance(dados, dict) else ""
        if not isinstance(cpf, str) or not re.fullmatch(
            r"[0-9]{11}|[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}", cpf
        ):
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse(
            {"erro": "Informe o CPF completo com 11 dígitos."}, status=400
        )
    cpf = re.sub(r"\D", "", cpf)
    # Histórico de compras, independentemente da data/status do painel.
    entrega = Entrega.objects.filter(cpf=cpf).order_by("-criado_em", "-id").first()
    cliente = (
        {
            campo: getattr(entrega, campo)
            for campo in ("cpf", "nome", "telefone", "endereco")
        }
        if entrega
        else None
    )
    return JsonResponse({"cliente": cliente})


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
            filtro |= Q(numero_diario=int(busca.lstrip("#")))
        if re.fullmatch(r"[0-9.\-\s]+", busca):
            cpf = re.sub(r"\D", "", busca)
            if cpf:
                filtro |= Q(cpf__contains=cpf)
        entregas = entregas.filter(filtro)
    return entregas


@login_required
@never_cache
@ensure_csrf_cookie
def inicio(request):
    return render(
        request,
        "entregas/inicio.html",
        {"hoje": timezone.localdate().isoformat(), "fuso": settings.TIME_ZONE},
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
                "hoje": timezone.localdate().isoformat(),
                "entregadores": list(Entregador.objects.values("id", "nome", "ativo")),
            }
        )
    try:
        dados = json.loads(request.body)
        if not isinstance(dados, dict):
            raise ValueError
        requisicao = uuid.UUID(str(dados.get("requisicao", "")))
    except (ValueError, TypeError):
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
    except (ValueError, TypeError):
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
            if proximo == Entrega.Status.EM_ROTA:
                if "entregador" in dados:
                    try:
                        candidato = Entregador.objects.filter(
                            pk=int(dados["entregador"]), ativo=True
                        ).first()
                    except (ValueError, TypeError, OverflowError):
                        candidato = None
                elif "responsavel" in dados:
                    nome = dados["responsavel"]
                    candidato = (
                        Entregador.objects.filter(nome=nome.strip(), ativo=True).first()
                        if isinstance(nome, str)
                        else None
                    )
                else:
                    candidato = Entregador.objects.filter(
                        pk=entrega.entregador_id, ativo=True
                    ).first()
                if not candidato:
                    return JsonResponse(
                        {
                            "erro": "Selecione um entregador ativo e cadastrado antes de iniciar a rota."
                        },
                        status=400,
                    )
                entrega.entregador = candidato
                entrega.responsavel = candidato.nome
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


@login_required
@never_cache
@require_GET
def roteiro(request):
    try:
        valores = request.GET.get("ids", "").split(",")
        if not 1 <= len(valores) <= 100 or any(
            not valor.isascii() or not valor.isdigit() or len(valor) > 18
            for valor in valores
        ):
            raise ValueError
        ids = list(dict.fromkeys(int(valor) for valor in valores))
        registros = Entrega.objects.in_bulk(ids)
        if len(registros) != len(ids):
            raise ValueError
    except ValueError:
        return render(
            request,
            "entregas/roteiro.html",
            {"erro": "Selecione de 1 a 100 entregas existentes para emitir o roteiro."},
            status=400,
        )
    entregas = [
        registros[pk] for pk in ids if registros[pk].status == Entrega.Status.PENDENTE
    ]
    if not entregas:
        return render(
            request,
            "entregas/roteiro.html",
            {
                "erro": "Nenhuma entrega pendente na seleção. Somente entregas pendentes podem compor o roteiro."
            },
            status=400,
        )
    return render(
        request,
        "entregas/roteiro.html",
        {
            "entregas": entregas,
            "total_volumes": sum(entrega.volumes for entrega in entregas),
            "emitido_em": timezone.now(),
            "ignoradas": len(ids) - len(entregas),
        },
    )


@login_required
@never_cache
@ensure_csrf_cookie
def cadastro_entregadores(request):
    return render(request, "entregas/entregadores.html")


def dados_entregador(item):
    return {
        "id": item.pk,
        "nome": item.nome,
        "telefone": item.telefone,
        "ativo": item.ativo,
        "versao": item.versao,
    }


@require_http_methods(["GET", "POST"])
@api_login
def entregadores(request):
    if request.method == "GET":
        return JsonResponse(
            {
                "entregadores": [
                    dados_entregador(item) for item in Entregador.objects.all()
                ]
            }
        )
    return salvar_entregador(request)


@require_http_methods(["PATCH"])
@api_login
def editar_entregador(request, pk):
    return salvar_entregador(request, pk)


def salvar_entregador(request, pk=None):
    try:
        dados = json.loads(request.body)
        if not isinstance(dados, dict) or not isinstance(dados.get("ativo"), bool):
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse(
            {"erro": "Dados inválidos para o cadastro do entregador."}, status=400
        )
    with transaction.atomic():
        item = (
            get_object_or_404(Entregador.objects.select_for_update(), pk=pk)
            if pk
            else None
        )
        if item and dados.get("versao") != item.versao:
            return JsonResponse(
                {
                    "erro": "Este cadastro foi alterado. Atualize a tabela e tente novamente."
                },
                status=409,
            )
        form = EntregadorForm(dados, instance=item)
        if not form.is_valid():
            return JsonResponse({"erros": form.errors}, status=400)
        item = form.save(commit=False)
        if pk:
            item.versao += 1
        item.save()
    return JsonResponse(
        {"entregador": dados_entregador(item)}, status=200 if pk else 201
    )

import json
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from .models import Entrega, EventoEntrega


@pytest.fixture
def operador(db):
    return get_user_model().objects.create_user("operador", password="Senha-teste-482!")


@pytest.fixture
def cliente(operador):
    client = Client()
    client.force_login(operador)
    return client


@pytest.fixture
def dados():
    return {
        "nome": "Maria da Silva",
        "endereco": "Rua das Flores, 45, Centro",
        "telefone": "(11) 99999-1234",
        "cupom": "45872",
        "volumes": 3,
        "data": timezone.localdate().isoformat(),
        "horario": "14:30",
        "responsavel": "Carlos",
        "observacoes": "Chamar na portaria",
        "requisicao": str(uuid.uuid4()),
    }


def cadastrar(cliente, dados):
    return cliente.post(reverse("lista"), dados, content_type="application/json")


def alterar(cliente, entrega, **dados):
    return cliente.patch(
        reverse("detalhe", args=[entrega["id"]]),
        {"versao": entrega["versao"], **dados},
        content_type="application/json",
    )


@pytest.mark.django_db
def test_acesso_exige_login():
    client = Client()
    assert client.get("/").status_code == 302
    assert client.get(reverse("lista")).status_code == 401
    assert client.get(reverse("exportar")).status_code == 401


def test_cadastro_sequencial_idempotente_e_auditado(cliente, dados):
    response = cadastrar(cliente, dados)
    assert response.status_code == 201
    primeiro = response.json()["entrega"]
    assert primeiro["status"] == "pendente"
    assert len(primeiro["sequencia"]) >= 6
    repetida = cadastrar(cliente, dados)
    assert repetida.json()["entrega"]["id"] == primeiro["id"]
    assert Entrega.objects.count() == 1
    dados["requisicao"] = str(uuid.uuid4())
    segundo = cadastrar(cliente, dados).json()["entrega"]
    assert segundo["id"] > primeiro["id"]
    assert EventoEntrega.objects.count() == 2


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("nome", "  "),
        ("endereco", ""),
        ("telefone", "123"),
        ("cupom", ""),
        ("volumes", 0),
        ("volumes", -1),
        ("volumes", 10000),
        ("volumes", 1.5),
        ("data", "inválida"),
        ("horario", "26:00"),
        ("requisicao", "inválida"),
    ],
)
def test_rejeita_dados_invalidos(cliente, dados, campo, valor):
    dados[campo] = valor
    assert cadastrar(cliente, dados).status_code == 400
    assert Entrega.objects.count() == 0


@pytest.mark.parametrize("payload", ["[]", "null", "{", '"texto"'])
def test_json_invalido(cliente, payload):
    assert (
        cliente.post(
            reverse("lista"), payload, content_type="application/json"
        ).status_code
        == 400
    )


def test_fluxo_completo_e_bloqueio_de_finalizada(cliente, dados):
    entrega = cadastrar(cliente, dados).json()["entrega"]
    assert alterar(cliente, entrega, status="entregue").status_code == 400
    rota = alterar(cliente, entrega, status="em_rota").json()["entrega"]
    final = alterar(cliente, rota, status="entregue").json()["entrega"]
    assert final["entregue_em"]
    assert alterar(cliente, final, status="pendente").status_code == 400
    assert alterar(cliente, final, **dados).status_code == 400
    detail = cliente.get(reverse("detalhe", args=[entrega["id"]])).json()
    assert len(detail["eventos"]) == 3


def test_exige_entregador_e_impede_remocao_em_rota(cliente, dados):
    dados["responsavel"] = ""
    entrega = cadastrar(cliente, dados).json()["entrega"]
    assert alterar(cliente, entrega, status="em_rota").status_code == 400
    dados["responsavel"] = "Ana"
    editada = alterar(cliente, entrega, **dados).json()["entrega"]
    rota = alterar(cliente, editada, status="em_rota").json()["entrega"]
    dados["responsavel"] = ""
    assert alterar(cliente, rota, **dados).status_code == 400


def test_edicao_concorrente_nao_sobrescreve(cliente, dados):
    entrega = cadastrar(cliente, dados).json()["entrega"]
    dados["nome"] = "Nome atualizado"
    assert alterar(cliente, entrega, **dados).status_code == 200
    assert alterar(cliente, entrega, status="cancelada").status_code == 409
    assert Entrega.objects.get().nome == "Nome atualizado"
    assert Entrega.objects.get().status == "pendente"


def test_cancelamento_preserva_historico(cliente, dados):
    entrega = cadastrar(cliente, dados).json()["entrega"]
    final = alterar(cliente, entrega, status="cancelada").json()["entrega"]
    assert final["status"] == "cancelada"
    assert final["entregue_em"] is None
    assert EventoEntrega.objects.count() == 2


def test_filtros_exportacao_e_ficha(cliente, dados):
    entrega = cadastrar(cliente, dados).json()["entrega"]
    assert (
        len(cliente.get(reverse("lista"), {"busca": "Maria"}).json()["entregas"]) == 1
    )
    assert (
        len(
            cliente.get(reverse("lista"), {"busca": f"#{entrega['sequencia']}"}).json()[
                "entregas"
            ]
        )
        == 1
    )
    assert (
        cliente.get(reverse("lista"), {"data": "2020-01-01"}).json()["entregas"] == []
    )
    assert cliente.get(reverse("lista"), {"data": "errada"}).status_code == 400
    response = cliente.get(reverse("exportar"))
    assert "Maria da Silva" in response.content.decode("utf-8-sig")
    assert response["Content-Type"].startswith("text/csv")
    assert (
        "Maria"
        not in cliente.get(reverse("exportar"), {"status": "entregue"}).content.decode()
    )
    ficha = cliente.get(reverse("ficha", args=[entrega["id"]]))
    assert "Super Baranda" in ficha.content.decode()
    assert entrega["sequencia"] in ficha.content.decode()
    assert (
        "private" not in ficha.get("Cache-Control", "")
        or "no-store" in ficha["Cache-Control"]
    )
    assert "no-store" in ficha["Cache-Control"]


def test_escape_html_e_formulas_csv(cliente, dados):
    dados["nome"] = '<script>alert("x")</script>'
    dados["cupom"] = '=HYPERLINK("https://example.org")'
    entrega = cadastrar(cliente, dados).json()["entrega"]
    ficha = cliente.get(reverse("ficha", args=[entrega["id"]])).content.decode()
    assert '<script>alert("x")</script>' not in ficha
    assert "&lt;script&gt;" in ficha
    export = cliente.get(reverse("exportar")).content.decode("utf-8-sig")
    assert "'=HYPERLINK" in export


def test_csrf_obrigatorio(operador, dados):
    client = Client(enforce_csrf_checks=True)
    client.force_login(operador)
    assert cadastrar(client, dados).status_code == 403
    client.get("/")
    response = client.post(
        reverse("lista"),
        json.dumps(dados),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )
    assert response.status_code == 201


def test_pwa_e_logout(cliente):
    worker = cliente.get(reverse("service-worker"))
    assert worker.status_code == 200
    assert worker["Service-Worker-Allowed"] == "/"
    assert worker["Content-Type"] == "application/javascript"
    assert cliente.get(reverse("logout")).status_code == 405
    assert cliente.post(reverse("logout")).status_code == 302
    assert cliente.get(reverse("lista")).status_code == 401

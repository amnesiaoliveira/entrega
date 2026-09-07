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


def test_roteiro_selecao_ordem_totais_e_escape(cliente, dados):
    primeira = cadastrar(cliente, dados).json()["entrega"]
    dados.update(
        nome="<script>alert(1)</script>", volumes=5, requisicao=str(uuid.uuid4())
    )
    segunda = cadastrar(cliente, dados).json()["entrega"]
    eventos_antes = EventoEntrega.objects.count()
    response = cliente.get(
        reverse("roteiro"), {"ids": f"{segunda['id']},{primeira['id']},{segunda['id']}"}
    )
    assert response.status_code == 200
    assert [entrega.pk for entrega in response.context["entregas"]] == [
        segunda["id"],
        primeira["id"],
    ]
    assert response.context["total_volumes"] == 8
    assert "&lt;script&gt;" in response.content.decode()
    assert "<script>alert(1)</script>" not in response.content.decode()
    assert "no-store" in response["Cache-Control"]
    assert EventoEntrega.objects.count() == eventos_antes
    assert not Entrega.objects.exclude(status="pendente").exists()


@pytest.mark.parametrize(
    "ids", ["", "abc", "-1", "0", "1,,2", "9" * 19, ",".join(["1"] * 101)]
)
def test_roteiro_rejeita_selecao_invalida(cliente, ids):
    response = cliente.get(reverse("roteiro"), {"ids": ids})
    assert response.status_code == 400
    assert "Selecione de 1 a 100" in response.content.decode()


def test_roteiro_nao_omite_entrega_inexistente(cliente, dados):
    entrega = cadastrar(cliente, dados).json()["entrega"]
    assert (
        cliente.get(reverse("roteiro"), {"ids": f"{entrega['id']},999999"}).status_code
        == 400
    )


@pytest.mark.django_db
def test_roteiro_exige_login():
    assert Client().get(reverse("roteiro"), {"ids": "1"}).status_code == 302


def test_roteiro_ignora_outros_status_e_recalcula_totais(cliente, dados):
    selecionadas = []
    for estado in ["pendente", "em_rota", "entregue", "cancelada", "pendente"]:
        dados["requisicao"] = str(uuid.uuid4())
        item = cadastrar(cliente, dados).json()["entrega"]
        Entrega.objects.filter(pk=item["id"]).update(status=estado)
        selecionadas.append(item["id"])
    response = cliente.get(
        reverse("roteiro"), {"ids": ",".join(map(str, reversed(selecionadas)))}
    )
    assert response.status_code == 200
    assert [item.pk for item in response.context["entregas"]] == [
        selecionadas[4],
        selecionadas[0],
    ]
    assert response.context["total_volumes"] == 6
    assert response.context["ignoradas"] == 3
    for pk in selecionadas[1:4]:
        assert f'data-id="{pk}"' not in response.content.decode()


@pytest.mark.parametrize("estado", ["em_rota", "entregue", "cancelada"])
def test_roteiro_sem_pendentes_nao_oferece_impressao(cliente, dados, estado):
    item = cadastrar(cliente, dados).json()["entrega"]
    # A situação pode mudar depois da seleção, antes de abrir a guia.
    Entrega.objects.filter(pk=item["id"]).update(status=estado)
    response = cliente.get(reverse("roteiro"), {"ids": item["id"]})
    assert response.status_code == 400
    html = response.content.decode()
    assert "Nenhuma entrega pendente" in html
    assert 'id="print-route"' not in html
    assert 'class="stop"' not in html


def test_iniciar_rota_atribui_entregador_na_mesma_operacao(cliente, dados):
    dados["responsavel"] = ""
    entrega = cadastrar(cliente, dados).json()["entrega"]
    resposta = alterar(cliente, entrega, status="em_rota", responsavel="  Carlos  ")
    assert resposta.status_code == 200
    registro = Entrega.objects.get()
    assert registro.status == "em_rota"
    assert registro.responsavel == "Carlos"
    assert registro.versao == 2
    assert registro.eventos.count() == 2


@pytest.mark.parametrize("responsavel", [None, [], "x" * 101, "   "])
def test_iniciar_rota_rejeita_entregador_invalido(cliente, dados, responsavel):
    entrega = cadastrar(cliente, dados).json()["entrega"]
    assert (
        alterar(cliente, entrega, status="em_rota", responsavel=responsavel).status_code
        == 400
    )
    registro = Entrega.objects.get()
    assert registro.status == "pendente"
    assert registro.responsavel == dados["responsavel"]
    assert registro.versao == 1

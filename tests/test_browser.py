"""Teste real em Chromium; usa banco isolado do Django, nunca o banco da loja."""

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from django.utils import timezone
from playwright.sync_api import expect, sync_playwright

from entregas.models import Entrega, Entregador

RESULTS = Path(__file__).resolve().parent.parent / "test-results"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TestNavegador(StaticLiveServerTestCase):
    def test_cadastro_entregador_e_selecao_na_entrega(self):
        get_user_model().objects.create_user("cadastro", password="Senha-teste-482!")
        RESULTS.mkdir(exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(self.live_server_url)
            page.get_by_label("Usuário", exact=True).fill("cadastro")
            page.get_by_label("Senha", exact=True).fill("Senha-teste-482!")
            page.get_by_role("button", name="Entrar no painel").click()
            page.get_by_role("link", name="Entregadores", exact=True).click()
            page.get_by_role("button", name="Novo entregador").click()
            page.get_by_label("Nome completo *", exact=True).fill("João Lima")
            page.get_by_label("Telefone", exact=True).fill("11999991234")
            expect(page.get_by_label("Telefone", exact=True)).to_have_value(
                "(11) 99999-1234"
            )
            page.get_by_role("button", name="Salvar entregador").click()
            expect(page.locator("#courier-list tr")).to_have_count(1)
            page.get_by_role("button", name="Editar", exact=True).click()
            page.get_by_label("Nome completo *", exact=True).fill("João da Silva")
            page.get_by_role("button", name="Salvar entregador").click()
            expect(page.locator("#courier-list")).to_contain_text("João da Silva")
            page.get_by_role("button", name="Inativar", exact=True).click()
            expect(page.locator("#courier-list .badge")).to_have_text("Inativo")
            page.get_by_role("button", name="Reativar", exact=True).click()
            expect(page.locator("#courier-list .badge")).to_have_text("Ativo")
            page.screenshot(path=str(RESULTS / "entregadores.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.get_by_role("link", name="Controle de entregas").click()
            expect(page.locator("#stat-total")).to_have_text("0")
            page.get_by_role("button", name="Nova entrega", exact=True).click()
            page.get_by_label("Entregador", exact=True).select_option(
                label="João da Silva"
            )
            expect(
                page.locator('select[name="entregador"] option:checked')
            ).to_have_text("João da Silva")
            browser.close()

    @override_settings(TIME_ZONE="America/La_Paz")
    def test_virada_do_dia_atualiza_painel_sem_apagar_historico(self):
        usuario = get_user_model().objects.create_user(
            "virada", password="Senha-teste-482!"
        )
        instante = datetime(2026, 9, 8, 3, 59, 50, tzinfo=UTC)
        Entrega.objects.create(
            nome="Entrega do dia anterior",
            endereco="Rua Um, 1",
            telefone="11999991234",
            cupom="123",
            volumes=1,
            data="2026-09-07",
            criado_por=usuario,
        )
        with (
            patch("django.utils.timezone.now", return_value=instante) as relogio,
            sync_playwright() as playwright,
        ):
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.clock.install(time=instante)
            page.goto(self.live_server_url)
            page.get_by_label("Usuário", exact=True).fill("virada")
            page.get_by_label("Senha", exact=True).fill("Senha-teste-482!")
            page.get_by_role("button", name="Entrar no painel").click()
            expect(page.locator("#stat-total")).to_have_text("1")
            expect(page.locator("#date")).to_have_value("2026-09-07")
            page.locator("#select-page").check()
            relogio.return_value = instante + timedelta(seconds=31)
            page.clock.fast_forward(31000)
            expect(page.locator("#date")).to_have_value("2026-09-08")
            expect(page.locator("#stat-total")).to_have_text("0")
            expect(page.locator("#emit-route")).to_be_disabled()
            page.get_by_role("button", name="Todas as entregas", exact=True).click()
            expect(page.locator("#stat-total")).to_have_text("1")
            browser.close()

    def test_operacao_pwa_desktop_mobile_e_offline(self):
        Entregador.objects.bulk_create(
            [Entregador(nome="Carlos Oliveira"), Entregador(nome="Pedro Souza")]
        )
        RESULTS.mkdir(exist_ok=True)
        get_user_model().objects.create_superuser(
            "operador", password="Senha-do-teste-482!", first_name="Operador"
        )
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.live_server_url)
            page.get_by_label("Usuário", exact=True).fill("operador")
            page.get_by_label("Senha", exact=True).fill("Senha-do-teste-482!")
            page.get_by_role("button", name="Entrar no painel").click()
            expect(page.locator("#stat-total")).to_have_text("0")
            page.get_by_role("button", name="Nova entrega", exact=True).click()
            page.get_by_label("Nome completo *", exact=True).fill("Maria da Silva")
            page.locator("#delivery-dialog [aria-label='Fechar']").click()
            page.get_by_role("button", name="Nova entrega", exact=True).click()
            expect(page.get_by_label("Nome completo *", exact=True)).to_have_value(
                "Maria da Silva"
            )
            page.get_by_label("Endereço completo *", exact=True).fill(
                "Rua das Flores, 245 · Centro"
            )
            page.get_by_label("Telefone *", exact=True).fill("(11) 99999-1234")
            page.get_by_label("Número do cupom *", exact=True).fill("45872")
            page.get_by_label("Quantidade de volumes *", exact=True).fill("3")
            page.get_by_role("button", name="Salvar entrega", exact=True).click()
            expect(page.locator("#stat-total")).to_have_text("1")
            expect(page.locator("#delivery-dialog")).not_to_be_visible()
            assert page.evaluate("localStorage.getItem('baranda.draft.1')") is None
            expect(page.get_by_role("columnheader", name="AÇÕES")).to_be_visible()
            expect(page.locator('[data-action="edit"]')).to_have_count(0)
            expect(page.locator('[data-action="print"]')).to_have_count(0)
            page.get_by_role("button", name="Iniciar rota").click()
            page.locator("#confirm-action").click()
            expect(page.locator("#confirm-error")).to_contain_text("entregador")
            page.get_by_label("Entregador da rota *", exact=True).select_option(
                label="Carlos Oliveira"
            )
            page.locator("#confirm-action").click()
            expect(page.locator("#stat-em_rota")).to_have_text("1")
            expect(page.locator('[data-action="start"]')).to_have_count(0)
            expect(page.locator('[data-action="cancel"]')).to_have_count(1)
            page.get_by_role("button", name="Editar", exact=True).click()
            page.get_by_label("Observações", exact=True).fill("Chamar na portaria")
            page.get_by_role("button", name="Salvar entrega", exact=True).click()
            expect(page.locator("#delivery-dialog")).not_to_be_visible()
            with context.expect_page() as receipt_info:
                page.get_by_role("button", name="Imprimir ficha").click()
            receipt = receipt_info.value
            receipt.wait_for_load_state()
            expect(receipt.locator("#nome-completo")).to_have_value("Maria da Silva")
            expect(receipt.locator("#numero-sequencia")).not_to_have_value("")
            receipt.pdf(path=str(RESULTS / "ficha.pdf"), prefer_css_page_size=True)
            receipt.close()
            page.get_by_role("button", name="Confirmar entrega").click()
            page.locator("#confirm-action").click()
            expect(page.locator("#stat-entregue")).to_have_text("1")
            expect(page.locator("[data-online-action]")).to_have_count(0)
            page.locator(".row-open").click()
            expect(page.locator(".timeline li")).to_have_count(4)
            page.locator("#detail-dialog [data-close]").click()
            with page.expect_download() as download_info:
                page.get_by_role("button", name="Exportar", exact=True).click()
            download_info.value.save_as(str(RESULTS / "entregas.csv"))
            assert "Maria da Silva" in (RESULTS / "entregas.csv").read_text(
                encoding="utf-8-sig"
            )

            # Dados ilustrativos apenas no banco temporário do teste.
            samples = [
                (
                    "Ana Carolina Santos",
                    "Av. Brasil, 1200 · Jardim América",
                    "pendente",
                    "",
                    4,
                ),
                (
                    "Roberto Almeida",
                    "Rua São Paulo, 89 · Centro",
                    "em_rota",
                    "Carlos Oliveira",
                    2,
                ),
                (
                    "Juliana Ferreira",
                    "Rua das Palmeiras, 312 · Boa Vista",
                    "entregue",
                    "Pedro Souza",
                    6,
                ),
                (
                    "Marcos Henrique",
                    "Av. Independência, 560 · Centro",
                    "pendente",
                    "",
                    3,
                ),
                (
                    "Fernanda Costa",
                    "Rua Paraná, 47 · Vila Nova",
                    "em_rota",
                    "Pedro Souza",
                    2,
                ),
                (
                    "Paulo Rodrigues",
                    "Rua dos Ipês, 198 · Jardim Europa",
                    "entregue",
                    "Carlos Oliveira",
                    5,
                ),
                (
                    "Camila Oliveira",
                    "Av. das Nações, 720 · São José",
                    "pendente",
                    "",
                    1,
                ),
                ("Lucas Martins", "Rua Bahia, 95 · Centro", "cancelada", "", 2),
                (
                    "Beatriz Lima",
                    "Rua XV de Novembro, 321 · Centro",
                    "entregue",
                    "Pedro Souza",
                    4,
                ),
            ]
            csrf = next(
                cookie["value"]
                for cookie in context.cookies()
                if cookie["name"] == "csrftoken"
            )
            for index, (nome, endereco, status, responsavel, volumes) in enumerate(
                samples
            ):
                created = page.request.post(
                    self.live_server_url + "/api/entregas/",
                    headers={"X-CSRFToken": csrf},
                    data={
                        "nome": nome,
                        "endereco": endereco,
                        "responsavel": responsavel,
                        "volumes": volumes,
                        "telefone": "(11) 99999-0000",
                        "cupom": str(45873 + index),
                        "data": timezone.localdate().isoformat(),
                        "horario": f"{13 + index // 4}:30",
                        "requisicao": str(uuid.uuid4()),
                    },
                )
                assert created.status == 201
                entrega = created.json()["entrega"]
                transitions = (
                    ["em_rota", "entregue"]
                    if status == "entregue"
                    else [status]
                    if status != "pendente"
                    else []
                )
                for next_status in transitions:
                    changed = page.request.patch(
                        f"{self.live_server_url}/api/entregas/{entrega['id']}/",
                        headers={"X-CSRFToken": csrf},
                        data={"status": next_status, "versao": entrega["versao"]},
                    )
                    assert changed.status == 200
                    entrega = changed.json()["entrega"]
            page.get_by_role("button", name="Atualizar entregas").click()
            expect(page.locator("#stat-total")).to_have_text("10")
            expect(page.locator("#delivery-list tr")).to_have_count(8)
            expect(page.locator("#emit-route")).to_be_disabled()
            page.get_by_role(
                "checkbox", name="Selecionar entregas desta página"
            ).check()
            expect(page.locator("#selection-count")).to_contain_text("8 selecionada(s)")
            page.get_by_role("button", name="Próxima página").click()
            page.get_by_role(
                "checkbox", name="Selecionar entregas desta página"
            ).check()
            expect(page.locator("#selection-count")).to_contain_text(
                "10 selecionada(s)"
            )
            page.locator(".status-tabs [data-status='em_rota']").click()
            expect(page.locator("#selection-count")).to_contain_text(
                "10 selecionada(s)"
            )
            with context.expect_page() as route_info:
                page.get_by_role("button", name="Emitir guia de roteiro").click()
            route = route_info.value
            route.wait_for_load_state()
            route.on("pageerror", lambda error: errors.append(str(error)))
            expect(route.locator(".stop")).to_have_count(3)
            expect(route.locator(".totals")).to_contain_text("8 volumes")
            expect(route.locator("#route-exclusions")).to_contain_text(
                "7 entregas ignoradas"
            )
            before = route.locator(".stop").first.get_attribute("data-id")
            route.locator(".stop").first.locator('[data-move="1"]').click()
            assert route.locator(".stop").nth(1).get_attribute("data-id") == before
            expect(route.locator(".stop-number").nth(1)).to_have_text("2")
            route.pdf(path=str(RESULTS / "roteiro.pdf"), prefer_css_page_size=True)
            route.set_viewport_size({"width": 390, "height": 844})
            assert route.evaluate("document.documentElement.scrollWidth <= innerWidth")
            route.screenshot(path=str(RESULTS / "roteiro-mobile.png"), full_page=True)
            route.close()
            page.get_by_role("button", name="Limpar seleção").click()
            expect(page.locator("#emit-route")).to_be_disabled()
            page.locator(".status-tabs [data-status='']").click()
            page.screenshot(path=str(RESULTS / "desktop.png"), full_page=True)
            page.get_by_role("button", name="Próxima página").click()
            expect(page.locator("#delivery-list tr")).to_have_count(2)
            page.get_by_role("button", name="Página anterior").click()
            page.locator(".status-tabs [data-status='em_rota']").click()
            expect(page.locator("#delivery-list tr")).to_have_count(2)
            page.locator(".status-tabs [data-status='']").click()
            page.get_by_role("searchbox", name="Buscar entregas").fill("Maria")
            expect(page.locator("#delivery-list tr")).to_have_count(1)
            page.get_by_role("searchbox", name="Buscar entregas").fill("")
            expect(page.locator("#stat-total")).to_have_text("10")

            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(RESULTS / "mobile.png"), full_page=True)
            page.get_by_role("button", name="Nova entrega", exact=True).click()
            assert page.locator("#delivery-dialog").evaluate(
                "el => el.scrollWidth <= el.clientWidth"
            )
            page.locator("#delivery-dialog [aria-label='Fechar']").click()
            page.evaluate("navigator.serviceWorker.ready")
            page.wait_for_function("navigator.serviceWorker.controller !== null")
            manifest = page.request.get(
                f"{self.live_server_url}/static/manifest.webmanifest"
            ).json()
            for item in manifest["icons"]:
                assert (
                    page.request.get(self.live_server_url + item["src"]).status == 200
                )
            context.set_offline(True)
            page.reload()
            expect(
                page.get_by_role("heading", name="Suas entregas, por perto.")
            ).to_be_visible()
            expect(page.locator(".offline-card")).to_have_count(10)
            page.get_by_role("searchbox").fill("Maria")
            expect(page.locator(".offline-card")).to_have_count(1)
            page.screenshot(path=str(RESULTS / "offline.png"), full_page=True)
            context.set_offline(False)
            page.get_by_role("link", name="Tentar reconectar").click()
            expect(page.locator("#stat-total")).to_have_text("10")
            page.get_by_role("button", name="Sair", exact=True).click()
            expect(page.get_by_role("button", name="Entrar no painel")).to_be_visible()
            assert page.evaluate("localStorage.getItem('baranda.offline')") is None
            context.set_offline(True)
            page.goto(self.live_server_url)
            expect(page.locator("#saved-at")).to_have_text(
                "Nenhuma consulta salva neste dispositivo."
            )
            assert errors == [], errors
            browser.close()

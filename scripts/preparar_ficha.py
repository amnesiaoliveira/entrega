"""Deriva a ficha Django do modelo original, preservando o layout fornecido."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
source = (ROOT / "template_controle_entrega.html").read_text(encoding="utf-8")
source = source.replace('data-sequencia=""', 'data-sequencia="{{ entrega.sequencia }}"')
source = source.replace(
    "<title>Controle de Entrega</title>",
    "<title>Entrega #{{ entrega.sequencia }} · Super Baranda</title>",
)
source = source.replace("Operação / Entregas", "Super Baranda / Entregas")
source = source.replace(
    "Preencha uma ficha para cada entrega.",
    "Entrega #{{ entrega.sequencia }} · {{ entrega.data|date:'d/m/Y' }} · {{ entrega.get_status_display }}",
)
fields = {
    'name="nomeCompleto" type="text"': 'name="nomeCompleto" type="text" value="{{ entrega.nome }}" readonly',
    '<textarea id="endereco-completo" name="enderecoCompleto"></textarea>': '<div class="address-value">{{ entrega.endereco|linebreaksbr }}</div>',
    'name="telefone" type="tel" inputmode="tel" maxlength="15"': 'name="telefone" type="tel" inputmode="tel" maxlength="15" value="{{ entrega.telefone }}" readonly',
    'name="numeroCupom" type="text"': 'name="numeroCupom" type="text" value="{{ entrega.cupom }}" readonly',
    'name="quantidadeVolumes" type="number" min="1"': 'name="quantidadeVolumes" type="number" min="1" value="{{ entrega.volumes }}" readonly',
    'name="numeroSequencia"': 'name="numeroSequencia" value="{{ entrega.sequencia }}"',
}
for old, new in fields.items():
    assert old in source, old
    source = source.replace(old, new)
for field, expression in {
    "nomeCompleto": "nome",
    "telefone": "telefone",
    "numeroCupom": "cupom",
    "quantidadeVolumes": "volumes",
    "numeroSequencia": "sequencia",
}.items():
    source = re.sub(
        rf'(<input\b[^>]*name="{field}"[^>]*>)',
        rf'\1<div class="print-value">{{{{ entrega.{expression} }}}}</div>',
        source,
    )
source = source.replace(
    "Confira o endereço e a quantidade de volumes antes da saída.",
    "Entregador: {{ entrega.responsavel|default:'A definir' }}. Confira o endereço e a quantidade de volumes antes da saída.",
)
source = source.replace(
    "</style>",
    """
    .address-value { border: 1px solid var(--field); padding: 10px 12px; min-height: 60px; font-size: 14px; overflow-wrap: anywhere; }
    .print-value { display: none; }
    @media print {
      .delivery-form { height: auto; min-height: 148mm; overflow: visible; }
      .address-value { min-height: 11mm; padding: 1.5mm 2mm; font-size: 8pt; }
      .helper { display: none; }
      input { display: none; }
      .print-value { display: block; border: 1px solid var(--field); min-height: 8mm; padding: 1.5mm 2mm; font-size: 9pt; overflow-wrap: anywhere; }
    }
  </style>""",
)
source = "{% load static %}\n" + source
source = source.replace("Imprimir meia folha A4", "Imprimir ficha compacta (A6)")
source = source.replace(
    "</head>",
    '<link rel="stylesheet" href="{% static \'ficha-compacta.css\' %}">\n<link rel="stylesheet" href="{% static \'theme.css\' %}">\n</head>',
)
(ROOT / "templates/entregas/ficha.html").write_text(source, encoding="utf-8")

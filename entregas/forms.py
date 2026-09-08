import re

from django import forms
from django.db.models import Q

from .models import Entrega, Entregador


class EntregadorForm(forms.ModelForm):
    class Meta:
        model = Entregador
        fields = ["nome", "telefone", "ativo"]

    def clean_nome(self):
        nome = " ".join(self.cleaned_data["nome"].split())
        if (
            Entregador.objects.filter(nome__iexact=nome)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("Já existe um entregador com este nome.")
        return nome

    def clean_telefone(self):
        telefone = self.cleaned_data["telefone"]
        if telefone and not 8 <= len(re.sub(r"\D", "", telefone)) <= 15:
            raise forms.ValidationError("Informe um telefone com 8 a 15 dígitos.")
        return telefone


class EntregaForm(forms.ModelForm):
    class Meta:
        model = Entrega
        fields = [
            "nome",
            "endereco",
            "telefone",
            "cupom",
            "volumes",
            "data",
            "horario",
            "entregador",
            "observacoes",
        ]

    def __init__(self, data=None, *args, **kwargs):
        # Aceita o nome enviado por versões anteriores da interface.
        if data is not None and "entregador" not in data and "responsavel" in data:
            data = data.copy()
            nome = data.get("responsavel", "")
            encontrado = (
                Entregador.objects.filter(nome=nome).first()
                if isinstance(nome, str) and nome
                else None
            )
            data["entregador"] = encontrado.pk if encontrado else "" if not nome else -1
        super().__init__(data, *args, **kwargs)
        self.fields["entregador"].queryset = Entregador.objects.filter(
            Q(ativo=True) | Q(pk=self.instance.entregador_id)
        )
        self._entregador_anterior = self.instance.entregador_id

    def save(self, commit=True):
        entrega = super().save(commit=False)
        if entrega._state.adding or entrega.entregador_id != self._entregador_anterior:
            entrega.responsavel = (
                entrega.entregador.nome if entrega.entregador_id else ""
            )
        if commit:
            entrega.save()
        return entrega

    def clean_telefone(self):
        telefone = self.cleaned_data["telefone"]
        if not 8 <= len(re.sub(r"\D", "", telefone)) <= 15:
            raise forms.ValidationError("Informe um telefone com 8 a 15 dígitos.")
        return telefone

    def clean_volumes(self):
        volumes = self.cleaned_data["volumes"]
        if volumes > 9999:
            raise forms.ValidationError("Informe no máximo 9.999 volumes.")
        return volumes

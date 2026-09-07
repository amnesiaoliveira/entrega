import re

from django import forms

from .models import Entrega


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
            "responsavel",
            "observacoes",
        ]

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

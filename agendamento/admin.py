from django.contrib import admin
from django.db.models import Sum

from smartwash.admin_site import admin_site
from .models import Agendamento, TipoLavagem


@admin.register(TipoLavagem, site=admin_site)
class TipoLavagemAdmin(admin.ModelAdmin):
    list_display = ("nome", "valor", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome",)


@admin.register(Agendamento, site=admin_site)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "nome", "placa", "tipo_lavagem", "valor_tipo", "horario")
    list_filter = ("criado_em", "tipo_lavagem")
    date_hierarchy = "criado_em"
    search_fields = ("nome", "email", "whatsapp", "placa")

    @admin.display(description="Valor (R$)")
    def valor_tipo(self, obj):
        return obj.tipo_lavagem.valor

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)

        try:
            qs = response.context_data["cl"].queryset
            total = qs.aggregate(total=Sum("tipo_lavagem__valor"))["total"] or 0
        except Exception:
            total = 0

        response.context_data["total_ganhos"] = total
        return response


# OBS:
# O model Horario NAO e registrado no Admin de proposito.
# Os horarios sao gerados automaticamente via comando/rotina "gerar_horarios".
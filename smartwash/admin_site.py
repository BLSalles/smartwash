from django.contrib.admin import AdminSite
from django.utils import timezone
from django.db.models import Sum

from agendamento.models import Agendamento


class SmartWashAdminSite(AdminSite):
    site_header = "SmartWash"
    site_title = "SmartWash Admin"
    index_title = "Dashboard"
    index_template = "admin/index.html"  # ✅ nosso template

    def index(self, request, extra_context=None):
        today = timezone.localdate()

        agendamentos_hoje = (
            Agendamento.objects
            .select_related("tipo_lavagem", "horario")
            .filter(horario__data=today)
            .order_by("horario__hora")
        )

        faturamento_hoje = agendamentos_hoje.aggregate(
            total=Sum("tipo_lavagem__valor")
        )["total"] or 0

        extra_context = extra_context or {}
        extra_context.update({
            "today": today,
            "agendamentos_hoje": agendamentos_hoje,
            "total_hoje": agendamentos_hoje.count(),
            "faturamento_hoje": faturamento_hoje,
        })

        return super().index(request, extra_context=extra_context)


admin_site = SmartWashAdminSite(name="smartwash_admin")
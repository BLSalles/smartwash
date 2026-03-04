import json
from datetime import date, timedelta

from django.contrib.admin import AdminSite
from django.db.models import Q, Sum
from django.utils import timezone

from lavagem.models import Agendamento, TipoLavagem


def _parse_date(value: str | None) -> date | None:
    """Parse YYYY-MM-DD (from <input type=date>) to date."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class SmartWashAdminSite(AdminSite):
    site_header = "SmartWash"
    site_title = "SmartWash Admin"
    index_title = "Dashboard"
    index_template = "admin/index.html"

    def index(self, request, extra_context=None):
        # ===== Base dates
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)
        week_end = today + timedelta(days=7)

        # ===== Read filters
        # If no explicit filter is provided, default to TODAY.
        f_de = request.GET.get("de")
        f_ate = request.GET.get("ate")
        f_tipo = request.GET.get("tipo")
        f_q = (request.GET.get("q") or "").strip()

        d_de = _parse_date(f_de) or today
        d_ate = _parse_date(f_ate) or today
        if d_ate < d_de:
            d_de, d_ate = d_ate, d_de

        # Normalized values back to template
        f_de_norm = d_de.isoformat()
        f_ate_norm = d_ate.isoformat()

        # ===== Queryset (base)
        qs = (
            Agendamento.objects
            .select_related("tipo_lavagem", "horario")
            .filter(horario__data__gte=d_de, horario__data__lte=d_ate)
        )

        if f_tipo:
            qs = qs.filter(tipo_lavagem_id=f_tipo)

        if f_q:
            qs = qs.filter(
                Q(nome__icontains=f_q)
                | Q(placa__icontains=f_q)
                | Q(whatsapp__icontains=f_q)
                | Q(email__icontains=f_q)
            )

        qs = qs.order_by("horario__data", "horario__hora")

        # ===== KPIs
        total_agendamentos = qs.count()
        total_faturamento = qs.aggregate(total=Sum("tipo_lavagem__valor"))["total"] or 0

        # ===== Agenda blocks (intuitive view)
        base_agenda = (
            Agendamento.objects
            .select_related("tipo_lavagem", "horario")
            .order_by("horario__data", "horario__hora")
        )

        # Apply only "tipo" and "q" to the daily blocks, so the admin can
        # still see the day view consistent with what they searched.
        if f_tipo:
            base_agenda = base_agenda.filter(tipo_lavagem_id=f_tipo)
        if f_q:
            base_agenda = base_agenda.filter(
                Q(nome__icontains=f_q)
                | Q(placa__icontains=f_q)
                | Q(whatsapp__icontains=f_q)
                | Q(email__icontains=f_q)
            )

        agenda_hoje = base_agenda.filter(horario__data=today)
        agenda_amanha = base_agenda.filter(horario__data=tomorrow)
        agenda_prox7 = base_agenda.filter(horario__data__gte=tomorrow, horario__data__lte=week_end)

        # ===== Recent list (within current filter)
        recent_agendamentos = qs.order_by("-horario__data", "-horario__hora", "-criado_em")[:20]

        # ===== Chart: faturamento por dia
        # If user filtered a range, use it; else show last 14 days.
        if request.GET.get("de") or request.GET.get("ate"):
            chart_start = d_de
            chart_end = d_ate
        else:
            chart_end = today
            chart_start = today - timedelta(days=13)

        agg = (
            Agendamento.objects
            .select_related("tipo_lavagem", "horario")
            .filter(horario__data__gte=chart_start, horario__data__lte=chart_end)
        )
        if f_tipo:
            agg = agg.filter(tipo_lavagem_id=f_tipo)
        if f_q:
            agg = agg.filter(
                Q(nome__icontains=f_q)
                | Q(placa__icontains=f_q)
                | Q(whatsapp__icontains=f_q)
                | Q(email__icontains=f_q)
            )

        by_day = {
            row["horario__data"]: float(row["total"] or 0)
            for row in agg.values("horario__data").annotate(total=Sum("tipo_lavagem__valor")).order_by("horario__data")
        }

        labels: list[str] = []
        totals: list[float] = []
        cur = chart_start
        while cur <= chart_end:
            labels.append(cur.strftime("%d/%m"))
            totals.append(by_day.get(cur, 0.0))
            cur += timedelta(days=1)

        tipos = TipoLavagem.objects.filter(ativo=True).order_by("nome")

        extra_context = extra_context or {}
        extra_context.update({
            # dates
            "today": today,
            "tomorrow": tomorrow,
            "week_end": week_end,

            # filters (normalized)
            "f_de": f_de_norm,
            "f_ate": f_ate_norm,
            "f_tipo": f_tipo or "",
            "f_q": f_q,
            "tipos": tipos,

            # dashboard content
            "agenda_hoje": agenda_hoje,
            "agenda_amanha": agenda_amanha,
            "agenda_prox7": agenda_prox7,
            "recent_agendamentos": recent_agendamentos,

            # KPIs
            "total_agendamentos": total_agendamentos,
            "total_faturamento": total_faturamento,

            # chart
            "chart_start": chart_start,
            "chart_end": chart_end,
            "chart_labels": json.dumps(labels, ensure_ascii=False),
            "chart_totals": json.dumps(totals, ensure_ascii=False),
        })

        return super().index(request, extra_context=extra_context)


admin_site = SmartWashAdminSite(name="smartwash_admin")

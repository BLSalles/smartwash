from __future__ import annotations

from datetime import date, datetime, timedelta

from django.contrib.admin import AdminSite
from django.db.models import Count, Q, Sum
from django.utils import timezone


def _parse_date(value: str) -> date | None:
    """Aceita YYYY-MM-DD (input type=date) e DD/MM/YYYY."""
    if not value:
        return None
    v = value.strip()
    try:
        return date.fromisoformat(v)
    except Exception:
        pass
    try:
        return datetime.strptime(v, "%d/%m/%Y").date()
    except Exception:
        return None


class SmartWashAdminSite(AdminSite):
    """Admin customizado para priorizar Agendamentos na home."""

    site_title = "SmartWash Admin"
    site_header = "SmartWash"
    index_title = "Agenda"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}

        from agendamento.models import Agendamento, TipoLavagem  # import local

        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)
        week_end = today + timedelta(days=7)

        # ====== filtros rápidos (GET) ======
        q = (request.GET.get("q") or "").strip()
        tipo = (request.GET.get("tipo") or "").strip()
        de_raw = (request.GET.get("de") or "").strip()
        ate_raw = (request.GET.get("ate") or "").strip()

        de = _parse_date(de_raw)
        ate = _parse_date(ate_raw)

        qs = (
            Agendamento.objects
            .select_related("horario", "tipo_lavagem")
            .order_by("-horario__data", "horario__hora", "-criado_em")
        )

        if q:
            qs = qs.filter(
                Q(nome__icontains=q)
                | Q(placa__icontains=q)
                | Q(whatsapp__icontains=q)
                | Q(email__icontains=q)
            )

        if tipo.isdigit():
            qs = qs.filter(tipo_lavagem_id=int(tipo))

        if de:
            qs = qs.filter(horario__data__gte=de)
        if ate:
            qs = qs.filter(horario__data__lte=ate)

        # ====== agenda por dia ======
        agenda_hoje = qs.filter(horario__data=today).order_by("horario__hora")
        agenda_amanha = qs.filter(horario__data=tomorrow).order_by("horario__hora")
        agenda_prox7 = (
            qs.filter(horario__data__gt=tomorrow, horario__data__lte=today + timedelta(days=7))
            .order_by("horario__data", "horario__hora")[:30]
        )

        # ====== KPIs ======
        total_agendamentos = qs.count()
        total_faturamento = qs.aggregate(total=Sum("tipo_lavagem__valor"))["total"] or 0

        # ====== gráfico de faturamento por dia ======
        # Se o usuário filtrar um período, usa esse período; se não, últimos 14 dias.
        chart_end = ate or today
        chart_start = de or (chart_end - timedelta(days=13))

        # Limita pra não explodir o gráfico em ranges gigantes
        if (chart_end - chart_start).days > 30:
            chart_start = chart_end - timedelta(days=30)

        por_dia = (
            qs.filter(horario__data__range=(chart_start, chart_end))
            .values("horario__data")
            .annotate(total=Sum("tipo_lavagem__valor"), qtd=Count("id"))
            .order_by("horario__data")
        )
        por_dia = {row["horario__data"]: row for row in por_dia}

        labels = []
        totals = []
        counts = []
        dias = (chart_end - chart_start).days + 1
        for i in range(dias):
            d = chart_start + timedelta(days=i)
            labels.append(d.strftime("%d/%m"))
            row = por_dia.get(d)
            totals.append(float(row["total"] or 0) if row else 0.0)
            counts.append(int(row["qtd"]) if row else 0)

        # ====== dados pro template ======
        extra_context.update(
            {
                "today": today,
                "tomorrow": tomorrow,
                "week_end": week_end,
                "tipos": TipoLavagem.objects.order_by("nome"),
                "f_q": q,
                "f_tipo": tipo,
                "f_de": de_raw,
                "f_ate": ate_raw,
                "agenda_hoje": agenda_hoje,
                "agenda_amanha": agenda_amanha,
                "agenda_prox7": agenda_prox7,
                "recent_agendamentos": qs[:20],
                "total_agendamentos": total_agendamentos,
                "total_faturamento": total_faturamento,
                "chart_labels": labels,
                "chart_totals": totals,
                "chart_counts": counts,
                "chart_start": chart_start,
                "chart_end": chart_end,
            }
        )

        return super().index(request, extra_context=extra_context)


admin_site = SmartWashAdminSite(name="smartwash_admin")

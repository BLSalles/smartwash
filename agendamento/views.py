from django.shortcuts import render, redirect
from .models import Horario, Agendamento

from django.shortcuts import render, redirect
from .models import Horario, Agendamento, TipoLavagem
from django.db import transaction
from django.utils.dateparse import parse_date

def agendar(request):
    data_str = request.GET.get("data")
    data = parse_date(data_str) if data_str else None

    tipos = TipoLavagem.objects.filter(ativo=True).order_by("nome")

    horarios = Horario.objects.none()
    if data:
        horarios = Horario.objects.filter(data=data, disponivel=True).order_by("hora")

    if request.method == "POST":
        horario_id = request.POST.get("horario")
        tipo_id = request.POST.get("tipo_lavagem")

        with transaction.atomic():
            # trava o horário pra evitar duplicar
            horario = Horario.objects.select_for_update().get(id=horario_id)

            if not horario.disponivel:
                return render(request, "agendar.html", {
                    "tipos": tipos,
                    "horarios": horarios,
                    "erro": "Esse horário já foi agendado. Escolha outro."
                })

            Agendamento.objects.create(
                nome=request.POST["nome"],
                email=request.POST["email"],
                whatsapp=request.POST["whatsapp"],
                placa=request.POST["placa"],
                tipo_lavagem_id=tipo_id,
                horario=horario
            )

            horario.disponivel = False
            horario.save(update_fields=["disponivel"])

        return redirect("sucesso")

    return render(request, "agendar.html", {"tipos": tipos, "horarios": horarios})

def sucesso(request):
    return render(request, "sucesso.html")
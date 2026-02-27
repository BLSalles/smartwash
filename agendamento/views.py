from django.shortcuts import render, redirect
from .models import Horario, Agendamento

def agendar(request):

    data = request.GET.get("data")

    horarios = []

    if data:
        horarios = Horario.objects.filter(
            data=data,
            agendamento__isnull=True
        ).order_by("hora")

    if request.method == "POST":

        horario_id = request.POST.get("horario")

        if Agendamento.objects.filter(horario_id=horario_id).exists():

            return render(request, "agendar.html", {
                "horarios": horarios,
                "erro": "Este horário já foi agendado."
            })

        Agendamento.objects.create(
            nome=request.POST.get("nome"),
            email=request.POST.get("email"),
            whatsapp=request.POST.get("whatsapp"),
            placa=request.POST.get("placa"),
            horario_id=horario_id
        )

        return redirect("sucesso")

    return render(request, "agendar.html", {
        "horarios": horarios
    })

def sucesso(request):
    return render(request, "sucesso.html")
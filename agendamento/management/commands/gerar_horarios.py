from django.core.management.base import BaseCommand
from agendamento.models import Horario
from datetime import datetime, date, time, timedelta


from django.core.management.base import BaseCommand
from agendamento.models import Horario
from datetime import time

class Command(BaseCommand):
    help = 'Gera horários das 08:00 às 18:00'

    def handle(self, *args, **kwargs):
        horarios = [
            "08:00",
            "09:00",
            "10:00",
            "11:00",
            "12:00",
            "13:00",
            "14:00",
            "15:00",
            "16:00",
            "17:00",
            "18:00",
        ]

        for h in horarios:
            Horario.objects.get_or_create(hora=h)

        self.stdout.write(self.style.SUCCESS("Horários criados com sucesso!"))
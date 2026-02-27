from django.contrib import admin
from .models import Horario, Agendamento


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ('data', 'hora', 'disponivel')
    list_filter = ('data', 'disponivel')


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'placa', 'whatsapp', 'horario', 'criado_em')
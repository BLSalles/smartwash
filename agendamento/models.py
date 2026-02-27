from django.db import models

class Horario(models.Model):
    data = models.DateField()
    hora = models.TimeField()
    disponivel = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.data} {self.hora}"


class Agendamento(models.Model):

    nome = models.CharField(max_length=100)
    email = models.EmailField()
    whatsapp = models.CharField(max_length=20)
    placa = models.CharField(max_length=10)

    horario = models.OneToOneField(
        Horario,
        on_delete=models.CASCADE
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} - {self.placa}"
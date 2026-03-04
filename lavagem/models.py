from django.db import models

class TipoLavagem(models.Model):
    nome = models.CharField(max_length=1000, unique=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nome} (R$ {self.valor})"

class Horario(models.Model):
    data = models.DateField()
    hora = models.TimeField()
    disponivel = models.BooleanField(default=True)

    class Meta:
        unique_together = ("data", "hora")

    def __str__(self):
        return f"{self.data} {self.hora}"


class Agendamento(models.Model):
    nome = models.CharField(max_length=1000)
    email = models.EmailField()
    whatsapp = models.CharField(max_length=1000)
    placa = models.CharField(max_length=1000)

    tipo_lavagem = models.ForeignKey(
        TipoLavagem,
        on_delete=models.PROTECT
    )

    horario = models.OneToOneField(
        Horario,
        on_delete=models.CASCADE
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} - {self.placa} - {self.tipo_lavagem.nome}"
from django.contrib import admin
from .models import PoliticaNoShow, Multa


@admin.register(PoliticaNoShow)
class PoliticaNoShowAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "empresa", "estado_consulta", "penalizacion_economica", "bloqueo_temporal", "dias_bloqueo", "activo")
    list_filter = ("empresa", "estado_consulta", "activo", "bloqueo_temporal")
    search_fields = ("nombre",)


@admin.register(Multa)
class MultaAdmin(admin.ModelAdmin):
    list_display = ("id", "empresa", "usuario", "consulta", "monto", "estado", "creado_en")
    list_filter = ("empresa", "estado", "creado_en")
    search_fields = ("usuario__nombre", "usuario__apellido", "consulta__id", "motivo")
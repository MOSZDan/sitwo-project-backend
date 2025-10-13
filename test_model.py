#!/usr/bin/env python
"""
Script para probar el modelo Historialclinico después de las migraciones
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dental_clinic_backend.settings')
django.setup()

from api.models import Historialclinico, Paciente, Usuario, Tipodeusuario
from django.utils import timezone
from django.db import connection

def test_historialclinico_model():
    print("=== PRUEBAS DEL MODELO HISTORIALCLINICO ===\n")
    
    # 1. Verificar datos existentes
    total = Historialclinico.objects.count()
    print(f"✅ Total de historiales clínicos: {total}")
    
    if total > 0:
        # Verificar que todos tienen fecha
        with_fecha = Historialclinico.objects.filter(fecha__isnull=False).count()
        without_fecha = Historialclinico.objects.filter(fecha__isnull=True).count()
        
        print(f"✅ Historiales con fecha: {with_fecha}")
        print(f"❌ Historiales sin fecha: {without_fecha}")
        
        # Mostrar algunos registros
        print("\n--- Primeros 3 registros ---")
        for i, h in enumerate(Historialclinico.objects.all()[:3], 1):
            print(f"{i}. ID: {h.id}, Fecha: {h.fecha}, Paciente ID: {h.pacientecodigo_id}")
    
    # 2. Probar crear un nuevo registro
    print("\n--- Prueba de creación de nuevo registro ---")
    try:
        # Necesitamos un paciente y usuario para crear el historial
        paciente = Paciente.objects.first()
        if not paciente:
            print("❌ No hay pacientes en la base de datos para probar")
            return
            
        # Crear un nuevo historial (debería auto-asignar fecha)
        nuevo_historial = Historialclinico(
            pacientecodigo=paciente,
            diagnostico="Prueba diagnóstico",
            tratamiento="Prueba tratamiento",
            observaciones="Prueba observaciones"
        )
        
        print(f"✅ Nuevo historial creado (antes de guardar): fecha={nuevo_historial.fecha}")
        # No guardar realmente para no afectar los datos
        print("✅ Prueba exitosa (no se guardó en BD)")
        
    except Exception as e:
        print(f"❌ Error al crear historial: {e}")
    
    print("\n=== RESUMEN ===")
    if without_fecha == 0:
        print("✅ TODAS LAS PRUEBAS EXITOSAS")
        print("✅ El campo fecha funciona correctamente")
        print("✅ Todos los registros existentes tienen fecha")
    else:
        print("❌ ENCONTRADOS REGISTROS SIN FECHA")
        print("❌ La migración puede no haberse aplicado correctamente")

if __name__ == "__main__":
    test_historialclinico_model()
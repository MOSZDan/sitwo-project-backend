#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para crear datos de prueba en el sistema SaaS Multi-Tenant
Crea 3 empresas de ejemplo con usuarios y datos básicos
"""

import os
import django
import sys
from pathlib import Path

# Fix encoding para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dental_clinic_backend.settings')
django.setup()

from api.models import (
    Empresa, Usuario, Tipodeusuario, Paciente, Odontologo,
    Recepcionista, Horario, Tipodeconsulta, Estado,
    Estadodeconsulta, Estadodefactura, Tipopago
)
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

User = get_user_model()


def create_base_data():
    """Crea datos base que necesita el sistema (roles, estados, etc.)"""
    print("📋 Creando datos base del sistema...")

    # Tipos de Usuario (Roles)
    roles = [
        {'id': 1, 'rol': 'Administrador', 'descripcion': 'Usuario con acceso completo al sistema'},
        {'id': 2, 'rol': 'Paciente', 'descripcion': 'Paciente de la clínica'},
        {'id': 3, 'rol': 'Recepcionista', 'descripcion': 'Personal de recepción'},
        {'id': 4, 'rol': 'Odontólogo', 'descripcion': 'Doctor odontólogo'},
    ]

    for rol_data in roles:
        rol, created = Tipodeusuario.objects.get_or_create(
            id=rol_data['id'],
            defaults={
                'rol': rol_data['rol'],
                'descripcion': rol_data['descripcion'],
                'empresa': None  # Los roles son globales
            }
        )
        if created:
            print(f"  ✅ Rol creado: {rol.rol}")

    # Estados
    estados = ['Pendiente', 'En Proceso', 'Completado', 'Cancelado']
    for nombre in estados:
        estado, created = Estado.objects.get_or_create(estado=nombre, empresa=None)
        if created:
            print(f"  ✅ Estado creado: {nombre}")

    # Estados de Consulta
    estados_consulta = ['Agendada', 'En Curso', 'Completada', 'Cancelada', 'Reprogramada']
    for nombre in estados_consulta:
        estado, created = Estadodeconsulta.objects.get_or_create(estado=nombre, empresa=None)
        if created:
            print(f"  ✅ Estado de consulta creado: {nombre}")

    # Estados de Factura
    estados_factura = ['Pendiente', 'Pagada', 'Vencida', 'Cancelada']
    for nombre in estados_factura:
        estado, created = Estadodefactura.objects.get_or_create(estado=nombre, empresa=None)
        if created:
            print(f"  ✅ Estado de factura creado: {nombre}")

    # Tipos de Pago
    tipos_pago = ['Efectivo', 'Tarjeta', 'Transferencia', 'QR']
    for nombre in tipos_pago:
        tipo, created = Tipopago.objects.get_or_create(nombrepago=nombre, empresa=None)
        if created:
            print(f"  ✅ Tipo de pago creado: {nombre}")

    # Tipos de Consulta
    tipos_consulta = [
        'Consulta General',
        'Limpieza Dental',
        'Ortodoncia',
        'Endodoncia',
        'Extracción',
        'Implante',
        'Blanqueamiento',
        'Urgencia'
    ]
    for nombre in tipos_consulta:
        tipo, created = Tipodeconsulta.objects.get_or_create(nombreconsulta=nombre, empresa=None)
        if created:
            print(f"  ✅ Tipo de consulta creado: {nombre}")

    # Horarios (8:00 AM - 6:00 PM, cada 30 minutos)
    from datetime import time
    horarios = []
    for hour in range(8, 18):
        for minute in [0, 30]:
            horarios.append(time(hour=hour, minute=minute))

    for hora in horarios:
        horario, created = Horario.objects.get_or_create(hora=hora, empresa=None)
        if created:
            print(f"  ✅ Horario creado: {hora.strftime('%H:%M')}")

    print("✅ Datos base creados exitosamente\n")


def create_empresa(nombre, subdomain):
    """Crea una empresa con datos de ejemplo"""
    print(f"🏢 Creando empresa: {nombre} ({subdomain})")

    # Crear empresa
    empresa, created = Empresa.objects.get_or_create(
        subdomain=subdomain,
        defaults={'nombre': nombre, 'activo': True}
    )

    if not created:
        print(f"  ⚠️  Empresa ya existe, actualizando datos...")

    # Crear usuario administrador
    rol_admin = Tipodeusuario.objects.get(id=1)

    email_admin = f"admin@{subdomain}.com"
    usuario_admin, created = Usuario.objects.get_or_create(
        correoelectronico=email_admin,
        defaults={
            'nombre': 'Admin',
            'apellido': nombre.split()[-1],
            'telefono': '+591 12345678',
            'sexo': 'Masculino',
            'idtipousuario': rol_admin,
            'empresa': empresa,
            'recibir_notificaciones': True,
            'notificaciones_email': True,
        }
    )

    if created:
        print(f"  ✅ Usuario admin creado: {email_admin}")
        # Crear usuario en Django auth
        User.objects.get_or_create(
            username=email_admin,
            defaults={
                'email': email_admin,
                'first_name': 'Admin',
                'last_name': nombre.split()[-1],
                'is_staff': True,
                'is_active': True,
                'password': make_password('admin123')
            }
        )

    # Crear odontólogo
    rol_odontologo = Tipodeusuario.objects.get(id=4)
    email_odontologo = f"doctor@{subdomain}.com"

    usuario_odontologo, created = Usuario.objects.get_or_create(
        correoelectronico=email_odontologo,
        defaults={
            'nombre': 'Dr. Juan',
            'apellido': 'Dentista',
            'telefono': '+591 23456789',
            'sexo': 'Masculino',
            'idtipousuario': rol_odontologo,
            'empresa': empresa,
            'recibir_notificaciones': True,
        }
    )

    if created:
        print(f"  ✅ Odontólogo creado: {email_odontologo}")

        odontologo, _ = Odontologo.objects.get_or_create(
            codusuario=usuario_odontologo,
            defaults={
                'especialidad': 'Odontología General',
                'experienciaprofesional': '10 años de experiencia',
                'nromatricula': f'ODO-{subdomain[:4].upper()}-001',
                'empresa': empresa
            }
        )

        # Usuario Django para login
        User.objects.get_or_create(
            username=email_odontologo,
            defaults={
                'email': email_odontologo,
                'first_name': 'Juan',
                'last_name': 'Dentista',
                'is_active': True,
                'password': make_password('doctor123')
            }
        )

    # Crear recepcionista
    rol_recepcionista = Tipodeusuario.objects.get(id=3)
    email_recepcionista = f"recepcion@{subdomain}.com"

    usuario_recepcionista, created = Usuario.objects.get_or_create(
        correoelectronico=email_recepcionista,
        defaults={
            'nombre': 'María',
            'apellido': 'Receptora',
            'telefono': '+591 34567890',
            'sexo': 'Femenino',
            'idtipousuario': rol_recepcionista,
            'empresa': empresa,
            'recibir_notificaciones': True,
        }
    )

    if created:
        print(f"  ✅ Recepcionista creada: {email_recepcionista}")

        Recepcionista.objects.get_or_create(
            codusuario=usuario_recepcionista,
            defaults={
                'habilidadessoftware': 'Microsoft Office, gestión de agendas',
                'empresa': empresa
            }
        )

        User.objects.get_or_create(
            username=email_recepcionista,
            defaults={
                'email': email_recepcionista,
                'first_name': 'María',
                'last_name': 'Receptora',
                'is_active': True,
                'password': make_password('recepcion123')
            }
        )

    # Crear pacientes de ejemplo
    rol_paciente = Tipodeusuario.objects.get(id=2)

    pacientes_data = [
        {'nombre': 'Carlos', 'apellido': 'Gómez', 'carnet': '12345678', 'fecha_nac': '1990-05-15'},
        {'nombre': 'Ana', 'apellido': 'Martínez', 'carnet': '23456789', 'fecha_nac': '1985-08-22'},
        {'nombre': 'Luis', 'apellido': 'Fernández', 'carnet': '34567890', 'fecha_nac': '1995-12-10'},
    ]

    for i, pac_data in enumerate(pacientes_data, 1):
        email_paciente = f"{pac_data['nombre'].lower()}.{pac_data['apellido'].lower()}@email.com"

        usuario_paciente, created = Usuario.objects.get_or_create(
            correoelectronico=email_paciente,
            defaults={
                'nombre': pac_data['nombre'],
                'apellido': pac_data['apellido'],
                'telefono': f'+591 4567890{i}',
                'sexo': 'Masculino' if i % 2 == 1 else 'Femenino',
                'idtipousuario': rol_paciente,
                'empresa': empresa,
                'recibir_notificaciones': True,
            }
        )

        if created:
            print(f"  ✅ Paciente creado: {email_paciente}")

            Paciente.objects.get_or_create(
                codusuario=usuario_paciente,
                defaults={
                    'carnetidentidad': pac_data['carnet'],
                    'fechanacimiento': pac_data['fecha_nac'],
                    'direccion': f'Calle {i}, Santa Cruz, Bolivia',
                    'empresa': empresa
                }
            )

            User.objects.get_or_create(
                username=email_paciente,
                defaults={
                    'email': email_paciente,
                    'first_name': pac_data['nombre'],
                    'last_name': pac_data['apellido'],
                    'is_active': True,
                    'password': make_password('paciente123')
                }
            )

    print(f"✅ Empresa {nombre} creada exitosamente\n")
    return empresa


def main():
    """Función principal"""
    print("=" * 60)
    print("🦷 CREAR DATOS DE PRUEBA - SaaS Multi-Tenant")
    print("=" * 60)
    print()

    # Crear datos base
    create_base_data()

    # Crear empresas de ejemplo
    empresas = [
        ('Clínica Dental Norte', 'norte'),
        ('Clínica Dental Sur', 'sur'),
        ('Clínica Dental Este', 'este'),
    ]

    for nombre, subdomain in empresas:
        create_empresa(nombre, subdomain)

    print("=" * 60)
    print("🎉 ¡DATOS DE PRUEBA CREADOS EXITOSAMENTE!")
    print("=" * 60)
    print()
    print("📝 CREDENCIALES CREADAS:")
    print()
    print("Empresa: Clínica Dental Norte (norte)")
    print("  Admin:        admin@norte.com / admin123")
    print("  Odontólogo:   doctor@norte.com / doctor123")
    print("  Recepcionista: recepcion@norte.com / recepcion123")
    print("  Pacientes:    carlos.gomez@email.com / paciente123")
    print()
    print("Empresa: Clínica Dental Sur (sur)")
    print("  Admin:        admin@sur.com / admin123")
    print("  Odontólogo:   doctor@sur.com / doctor123")
    print("  Recepcionista: recepcion@sur.com / recepcion123")
    print()
    print("Empresa: Clínica Dental Este (este)")
    print("  Admin:        admin@este.com / admin123")
    print("  Odontólogo:   doctor@este.com / doctor123")
    print("  Recepcionista: recepcion@este.com / recepcion123")
    print()
    print("🌐 URLs:")
    print("  Backend:      http://localhost:8000/api/")
    print("  Admin Django: http://localhost:8000/admin/")
    print("  Frontend Norte: http://norte.localhost:5174")
    print("  Frontend Sur:   http://sur.localhost:5174")
    print("  Frontend Este:  http://este.localhost:5174")
    print()
    print("💡 TIP: Configura tu archivo hosts para los subdominios locales")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
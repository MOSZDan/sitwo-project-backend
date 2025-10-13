# api/signals.py
"""
Signals para mantener consistencia de datos cuando se cambian roles de usuarios.

Cuando un Usuario cambia su idtipousuario (rol):
- Se elimina de la tabla del rol anterior
- Se crea en la tabla del rol nuevo
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from .models import Usuario, Paciente, Odontologo, Recepcionista, Tipodeusuario
import logging

logger = logging.getLogger(__name__)


def obtener_nombre_rol(tipo_usuario):
    """Helper para obtener el nombre del rol"""
    if not tipo_usuario:
        return None
    return tipo_usuario.rol.lower()


@receiver(pre_save, sender=Usuario)
def guardar_rol_anterior(sender, instance, **kwargs):
    """
    Pre-save: Guarda el rol anterior para comparar después.
    """
    if instance.pk:  # Solo si es actualización, no creación
        try:
            old_instance = Usuario.objects.get(pk=instance.pk)
            instance._old_idtipousuario = old_instance.idtipousuario
        except Usuario.DoesNotExist:
            instance._old_idtipousuario = None
    else:
        instance._old_idtipousuario = None


@receiver(post_save, sender=Usuario)
def sincronizar_rol_usuario(sender, instance, created, **kwargs):
    """
    Post-save: Sincroniza las tablas de roles cuando cambia idtipousuario.

    Casos:
    1. Creación (created=True): Crear en tabla correspondiente
    2. Actualización con cambio de rol: Eliminar de tabla anterior, crear en nueva
    3. Actualización sin cambio de rol: No hacer nada
    """

    # Ignorar si no tiene tipo de usuario
    if not instance.idtipousuario:
        logger.warning(f"Usuario {instance.codigo} sin tipo de usuario asignado")
        return

    nuevo_rol = obtener_nombre_rol(instance.idtipousuario)

    # Si es creación
    if created:
        logger.info(f"Creando registro de rol '{nuevo_rol}' para usuario {instance.codigo}")
        crear_registro_rol(instance, nuevo_rol)
        return

    # Si es actualización, verificar si cambió el rol
    old_tipo = getattr(instance, '_old_idtipousuario', None)

    if old_tipo and old_tipo.id != instance.idtipousuario.id:
        old_rol = obtener_nombre_rol(old_tipo)

        logger.info(
            f"Usuario {instance.codigo}: Cambio de rol '{old_rol}' → '{nuevo_rol}'"
        )

        with transaction.atomic():
            # Eliminar de tabla anterior
            eliminar_registro_rol(instance, old_rol)

            # Crear en tabla nueva
            crear_registro_rol(instance, nuevo_rol)


def crear_registro_rol(usuario, rol):
    """
    Crea un registro en la tabla correspondiente al rol.
    """
    try:
        if 'paciente' in rol:
            # Verificar si ya existe
            if not Paciente.objects.filter(codusuario=usuario).exists():
                Paciente.objects.create(
                    codusuario=usuario,
                    empresa=usuario.empresa,
                    # Campos opcionales con valores por defecto
                    carnetidentidad=None,
                    fechanacimiento=None,
                    direccion=None
                )
                logger.info(f"✅ Paciente creado para usuario {usuario.codigo}")
            else:
                logger.info(f"ℹ️  Paciente ya existe para usuario {usuario.codigo}")

        elif 'odontologo' in rol or 'odontólogo' in rol:
            if not Odontologo.objects.filter(codusuario=usuario).exists():
                Odontologo.objects.create(
                    codusuario=usuario,
                    empresa=usuario.empresa,
                    especialidad=None,
                    experienciaprofesional=None,
                    nromatricula=None
                )
                logger.info(f"✅ Odontólogo creado para usuario {usuario.codigo}")
            else:
                logger.info(f"ℹ️  Odontólogo ya existe para usuario {usuario.codigo}")

        elif 'recepcionista' in rol:
            if not Recepcionista.objects.filter(codusuario=usuario).exists():
                Recepcionista.objects.create(
                    codusuario=usuario,
                    empresa=usuario.empresa,
                    habilidadessoftware=None
                )
                logger.info(f"✅ Recepcionista creado para usuario {usuario.codigo}")
            else:
                logger.info(f"ℹ️  Recepcionista ya existe para usuario {usuario.codigo}")

        elif 'administrador' in rol:
            # Administradores no tienen tabla específica
            logger.info(f"ℹ️  Rol administrador no requiere tabla específica")

        else:
            logger.warning(f"⚠️  Rol desconocido: {rol}")

    except Exception as e:
        logger.error(f"❌ Error creando registro de rol '{rol}' para usuario {usuario.codigo}: {e}")


def eliminar_registro_rol(usuario, rol):
    """
    Elimina el registro de la tabla correspondiente al rol.
    """
    try:
        if 'paciente' in rol:
            deleted, _ = Paciente.objects.filter(codusuario=usuario).delete()
            if deleted:
                logger.info(f"🗑️  Paciente eliminado para usuario {usuario.codigo}")
            else:
                logger.info(f"ℹ️  No existía Paciente para usuario {usuario.codigo}")

        elif 'odontologo' in rol or 'odontólogo' in rol:
            deleted, _ = Odontologo.objects.filter(codusuario=usuario).delete()
            if deleted:
                logger.info(f"🗑️  Odontólogo eliminado para usuario {usuario.codigo}")
            else:
                logger.info(f"ℹ️  No existía Odontólogo para usuario {usuario.codigo}")

        elif 'recepcionista' in rol:
            deleted, _ = Recepcionista.objects.filter(codusuario=usuario).delete()
            if deleted:
                logger.info(f"🗑️  Recepcionista eliminado para usuario {usuario.codigo}")
            else:
                logger.info(f"ℹ️  No existía Recepcionista para usuario {usuario.codigo}")

        elif 'administrador' in rol:
            logger.info(f"ℹ️  Rol administrador no tiene tabla específica que eliminar")

        else:
            logger.warning(f"⚠️  Rol desconocido para eliminación: {rol}")

    except Exception as e:
        logger.error(f"❌ Error eliminando registro de rol '{rol}' para usuario {usuario.codigo}: {e}")
# api/views.py
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import get_user_model
from django.db import connection
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.utils.timezone import make_aware
from datetime import datetime, timedelta
import csv
from io import BytesIO

from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Paciente, Consulta, Odontologo, Horario, Tipodeconsulta,
    Usuario, Tipodeusuario, Vista, Bitacora
)

from .serializers import (
    PacienteSerializer,
    ConsultaSerializer,
    CreateConsultaSerializer,
    OdontologoMiniSerializer,
    HorarioSerializer,
    TipodeconsultaSerializer,
    UpdateConsultaSerializer,
    UsuarioAdminSerializer,
    TipodeusuarioSerializer,
    VistaSerializer,
    BitacoraSerializer,
    ReprogramarConsultaSerializer
)


# -------------------- Health / Utils --------------------

def health(request):
    """Ping de salud"""
    return JsonResponse({"ok": True})


def db_info(request):
    """Info rápida de la conexión a DB (útil en dev/diagnóstico)."""
    with connection.cursor() as cur:
        cur.execute("select current_database(), current_user")
        db, user = cur.fetchone()
    return JsonResponse({"database": db, "user": user})


def users_count(request):
    """
    Cuenta de usuarios del auth de Django (tabla auth_user).
    NOTA: devolvemos 'count' para cuadrar con el frontend.
    """
    User = get_user_model()
    return JsonResponse({"count": User.objects.count()})


# Helper reutilizable: ¿el usuario actual es admin en la tabla de negocio?
def _es_admin_por_tabla(dj_user) -> bool:
    email = (getattr(dj_user, "email", None) or getattr(dj_user, "username", "")).strip().lower()
    if not email:
        return False
    return Usuario.objects.filter(
        correoelectronico__iexact=email,
        idtipousuario_id=1  # 1 = Administrador
    ).exists()


# -------------------- Pacientes --------------------

class PacienteViewSet(ReadOnlyModelViewSet):
    """
    API read-only de Pacientes.
    Requiere sesión activa (IsAuthenticated) y trae el Usuario relacionado.
    """
    permission_classes = [IsAuthenticated]
    queryset = Paciente.objects.select_related("codusuario").all()
    serializer_class = PacienteSerializer


# -------------------- Consultas (Citas) --------------------

class ConsultaViewSet(ModelViewSet):
    """
    API para Consultas. Permite crear, leer, actualizar y eliminar.
    """
    permission_classes = [IsAuthenticated]
    queryset = (
        Consulta.objects.select_related(
            "codpaciente__codusuario",
            "cododontologo__codusuario",
            "codrecepcionista__codusuario",
            "idhorario",
            "idtipoconsulta",
            "idestadoconsulta",
        ).all()
    )
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['codpaciente', 'fecha']

    def get_serializer_class(self):
        # --- MODIFICACIÓN: Añadir el nuevo serializador ---
        if self.action == 'reprogramar':
            return ReprogramarConsultaSerializer
        if self.action in ["create", "update"]:
            return CreateConsultaSerializer
        if self.action == "partial_update":
            return UpdateConsultaSerializer
        return ConsultaSerializer

    # El método perform_create se mantiene igual para enviar correos

    def perform_create(self, serializer):
        consulta = serializer.save()
        paciente = consulta.codpaciente
        usuario_paciente = paciente.codusuario

        # Verificar si el usuario quiere recibir notificaciones por email
        if getattr(usuario_paciente, "notificaciones_email", False):
            try:
                subject = "Confirmación de tu cita en Clínica Dental"
                fecha_formateada = consulta.fecha.strftime('%d de %B de %Y')
                hora_formateada = consulta.idhorario.hora.strftime('%H:%M')

                message = f"""
Hola {usuario_paciente.nombre},

Tu cita ha sido agendada exitosamente con los siguientes detalles:

📅 Fecha: {fecha_formateada}
🕐 Hora: {hora_formateada}
👨‍⚕️ Odontólogo: Dr. {consulta.cododontologo.codusuario.nombre} {consulta.cododontologo.codusuario.apellido}
🦷 Tipo de consulta: {consulta.idtipoconsulta.nombreconsulta}

Recuerda llegar 15 minutos antes de tu cita.

¡Te esperamos en Smile Studio!

Si necesitas cancelar o reprogramar tu cita, ponte en contacto con nosotros.
                """

                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [usuario_paciente.correoelectronico]
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)

            except Exception as e:
                print(f"Error al enviar correo de notificación: {e}")


    @action(detail=True, methods=['patch'], url_path='reprogramar')
    def reprogramar(self, request, pk=None):
        """
        Reprograma una cita a una nueva fecha y/o horario.
        Valida que el nuevo horario esté libre.
        """
        consulta = self.get_object()

        # Pasamos la instancia de la consulta al contexto del serializador para la validación
        serializer = self.get_serializer(data=request.data, context={'consulta': consulta})
        serializer.is_valid(raise_exception=True)

        nueva_fecha = serializer.validated_data['fecha']
        nuevo_horario = serializer.validated_data['idhorario']

        # Actualizar la consulta
        consulta.fecha = nueva_fecha
        consulta.idhorario = nuevo_horario

        # Opcional: Cambiar estado a 'Reprogramada' si existe (ej. id=5)
        # consulta.idestadoconsulta_id = 5
        consulta.save()

        # TODO: Considera enviar una notificación de reprogramación por email

        return Response(
            {"detail": "La cita ha sido reprogramada exitosamente."},
            status=status.HTTP_200_OK
        )


    # --- NUEVA ACCIÓN: Cancelar Cita (eliminar definitivamente) ---
    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        """
        Cancela una cita eliminándola de la base de datos.
        """
        consulta = self.get_object()

        consulta_id = consulta.pk
        consulta.delete()

        # Opcional: enviar notificación de cancelación aquí

        return Response(
            {"detail": "La cita ha sido cancelada y eliminada.", "id": consulta_id},
            status=status.HTTP_200_OK
        )

# -------------------- Catálogos --------------------

class OdontologoViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Odontologo.objects.all()
    serializer_class = OdontologoMiniSerializer


class HorarioViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Horario.objects.all()
    serializer_class = HorarioSerializer


class TipodeconsultaViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Tipodeconsulta.objects.all()
    serializer_class = TipodeconsultaSerializer


# -------------------- ADMIN: Roles y Usuarios --------------------

class TipodeusuarioViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Tipodeusuario.objects.all().order_by("id")
    serializer_class = TipodeusuarioSerializer
    pagination_class = None


class UsuarioViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Usuario.objects.select_related("idtipousuario").all()
    serializer_class = UsuarioAdminSerializer

    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["nombre", "apellido", "correoelectronico"]
    ordering = ["apellido", "nombre"]

    lookup_field = "codigo"
    http_method_names = ["get", "patch", "head", "options"]

    def partial_update(self, request, *args, **kwargs):
        """
        Autorización: solo administradores pueden cambiar roles.
        Admin = user.is_staff OR Usuario.idtipousuario_id == 1 (buscando por email/username).
        """
        user = request.user
        is_staff = getattr(user, "is_staff", False)
        es_admin_tabla = _es_admin_por_tabla(user)

        if not (is_staff or es_admin_tabla):
            return Response({"detail": "Solo administradores pueden cambiar roles."}, status=403)

        return super().partial_update(request, *args, **kwargs)


# -------------------- NUEVO: Gestionar Permisos (Vistas) --------------------

class VistaViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Vista.objects.prefetch_related("roles_permitidos").all()
    serializer_class = VistaSerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def create(self, request, *args, **kwargs):
        if not (getattr(request.user, "is_staff", False) or _es_admin_por_tabla(request.user)):
            return Response({"detail": "Solo administradores."}, status=403)
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not (getattr(request.user, "is_staff", False) or _es_admin_por_tabla(request.user)):
            return Response({"detail": "Solo administradores."}, status=403)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not (getattr(request.user, "is_staff", False) or _es_admin_por_tabla(request.user)):
            return Response({"detail": "Solo administradores."}, status=403)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="mis-vistas")
    def mis_vistas(self, request):
        dom = getattr(request.user, "usuario", None)
        rol_id = getattr(dom, "idtipousuario_id", None)
        if not rol_id:
            return Response([], status=200)
        vistas = self.get_queryset().filter(roles_permitidos__id=rol_id)
        data = VistaSerializer(vistas, many=True).data
        return Response(data, status=200)


# -------------------- Perfil de Usuario --------------------

class UserProfileView(RetrieveUpdateAPIView):
    """
    Vista para leer y actualizar los datos del perfil del usuario autenticado.
    Soporta GET, PUT y PATCH.
    """
    # Necesitarías agregar UsuarioMeSerializer en serializers.py
    # serializer_class = UsuarioMeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        En lugar de devolver request.user directamente, buscamos el perfil 'Usuario'
        que está vinculado a ese usuario de autenticación.
        """
        try:
            usuario_perfil = Usuario.objects.get(correoelectronico__iexact=self.request.user.email)
            return usuario_perfil
        except Usuario.DoesNotExist:
            return None


# -------------------- Bitácora de Auditoría --------------------

# Reemplaza solo la clase BitacoraViewSet en tu api/views.py

class BitacoraViewSet(ReadOnlyModelViewSet):
    """
    API read-only para la Bitácora de auditoría.
    Solo usuarios admin pueden ver los registros.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = BitacoraSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['descripcion', 'usuario__nombre', 'usuario__apellido', 'ip_address']
    ordering_fields = ['fecha_hora', 'accion', 'usuario__nombre']
    ordering = ['-fecha_hora']  # Más recientes primero

    def get_queryset(self):
        # Solo admins pueden ver la bitácora
        if not _es_admin_por_tabla(self.request.user):
            return Bitacora.objects.none()

        queryset = Bitacora.objects.select_related('usuario').all()

        # Filtros opcionales por parámetros GET
        accion = self.request.query_params.get('accion', None)
        if accion:
            queryset = queryset.filter(accion=accion)

        usuario_id = self.request.query_params.get('usuario_id', None)
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)

        # Filtro por fechas
        fecha_desde = self.request.query_params.get('fecha_desde', None)
        fecha_hasta = self.request.query_params.get('fecha_hasta', None)

        if fecha_desde:
            try:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d')
                fecha_desde = make_aware(fecha_desde)
                queryset = queryset.filter(fecha_hora__gte=fecha_desde)
            except ValueError:
                pass

        if fecha_hasta:
            try:
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d')
                fecha_hasta = make_aware(fecha_hasta.replace(hour=23, minute=59, second=59))
                queryset = queryset.filter(fecha_hora__lte=fecha_hasta)
            except ValueError:
                pass

        return queryset

    @action(detail=False, methods=['get'], url_path='estadisticas')
    def estadisticas(self, request):
        """
        Endpoint para obtener estadísticas de la bitácora
        """
        if not _es_admin_por_tabla(request.user):
            return Response(
                {"detail": "No tienes permisos para ver las estadísticas."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Estadísticas de los últimos 30 días
        fecha_limite = make_aware(datetime.now() - timedelta(days=30))
        queryset = Bitacora.objects.filter(fecha_hora__gte=fecha_limite)

        # Contar por acción
        acciones = {}
        for registro in queryset:
            accion = registro.get_accion_display()
            acciones[accion] = acciones.get(accion, 0) + 1

        # Usuarios más activos
        usuarios_activos = {}
        for registro in queryset.filter(usuario__isnull=False).select_related('usuario'):
            nombre = f"{registro.usuario.nombre} {registro.usuario.apellido}"
            usuarios_activos[nombre] = usuarios_activos.get(nombre, 0) + 1

        # Ordenar usuarios por actividad
        usuarios_activos = dict(sorted(usuarios_activos.items(), key=lambda x: x[1], reverse=True)[:10])

        # Actividad por día (últimos 7 días)
        actividad_diaria = {}
        for i in range(7):
            fecha = datetime.now() - timedelta(days=i)
            fecha_str = fecha.strftime('%d/%m')
            inicio_dia = make_aware(fecha.replace(hour=0, minute=0, second=0, microsecond=0))
            fin_dia = make_aware(fecha.replace(hour=23, minute=59, second=59, microsecond=999999))

            count = queryset.filter(fecha_hora__range=[inicio_dia, fin_dia]).count()
            actividad_diaria[fecha_str] = count

        return Response({
            'total_registros': queryset.count(),
            'acciones': acciones,
            'usuarios_activos': usuarios_activos,
            'actividad_diaria': actividad_diaria,
            'periodo': 'Últimos 30 días'
        })

    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request):
        """
        Endpoint para exportar bitácora en CSV o PDF
        """
        if not _es_admin_por_tabla(request.user):
            return Response(
                {"detail": "No tienes permisos para exportar la bitácora."},
                status=status.HTTP_403_FORBIDDEN
            )

        format_type = request.query_params.get('format', 'csv').lower()

        # Obtener datos con filtros aplicados
        queryset = self.get_queryset()

        # Aplicar filtros de la query
        accion = request.query_params.get('accion', None)
        if accion:
            queryset = queryset.filter(accion=accion)

        fecha_desde = request.query_params.get('fecha_desde', None)
        fecha_hasta = request.query_params.get('fecha_hasta', None)

        if fecha_desde:
            try:
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d')
                fecha_desde = make_aware(fecha_desde)
                queryset = queryset.filter(fecha_hora__gte=fecha_desde)
            except ValueError:
                pass

        if fecha_hasta:
            try:
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d')
                fecha_hasta = make_aware(fecha_hasta.replace(hour=23, minute=59, second=59))
                queryset = queryset.filter(fecha_hora__lte=fecha_hasta)
            except ValueError:
                pass

        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(descripcion__icontains=search) |
                Q(usuario__nombre__icontains=search) |
                Q(usuario__apellido__icontains=search) |
                Q(ip_address__icontains=search)
            )

        if format_type == 'csv':
            return self._export_csv(queryset)
        elif format_type == 'pdf':
            return self._export_pdf(queryset)
        else:
            return Response({"detail": "Formato no soportado"}, status=status.HTTP_400_BAD_REQUEST)

    def _export_csv(self, queryset):
        """Exportar a CSV"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="bitacora_{datetime.now().strftime("%Y%m%d")}.csv"'

        # Agregar BOM para Excel
        response.write('\ufeff')

        writer = csv.writer(response)

        # Escribir headers
        writer.writerow([
            'Fecha/Hora',
            'Acción',
            'Usuario',
            'Descripción',
            'IP',
            'Navegador',
            'Modelo Afectado',
            'Objeto ID'
        ])

        # Escribir datos
        for entry in queryset[:1000]:  # Limitar a 1000 registros
            usuario_nombre = f"{entry.usuario.nombre} {entry.usuario.apellido}" if entry.usuario else "Usuario anónimo"

            writer.writerow([
                entry.fecha_hora.strftime('%d/%m/%Y %H:%M:%S'),
                entry.get_accion_display(),
                usuario_nombre,
                entry.descripcion or '',
                entry.ip_address,
                entry.user_agent or '',
                entry.modelo_afectado or '',
                entry.objeto_id or ''
            ])

        return response

    def _export_pdf(self, queryset):
        """Exportar a PDF"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        except ImportError:
            return Response(
                {"detail": "PDF export no disponible. Instale reportlab: pip install reportlab"},
                status=status.HTTP_400_BAD_REQUEST
            )

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Centrado
        )

        # Título
        title = Paragraph("Bitácora de Auditoría", title_style)
        elements.append(title)

        # Fecha de generación
        fecha_gen = Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
        elements.append(fecha_gen)
        elements.append(Spacer(1, 20))

        # Datos de la tabla
        data = [['Fecha/Hora', 'Acción', 'Usuario', 'Descripción', 'IP']]

        for entry in queryset[:100]:  # Limitar a 100 para PDF
            usuario_nombre = f"{entry.usuario.nombre} {entry.usuario.apellido}" if entry.usuario else "Anónimo"

            data.append([
                entry.fecha_hora.strftime('%d/%m/%Y %H:%M'),
                entry.get_accion_display(),
                usuario_nombre,
                (entry.descripcion or '')[:50] + '...' if len(entry.descripcion or '') > 50 else (
                        entry.descripcion or ''),
                entry.ip_address
            ])

        # Crear tabla
        table = Table(data, colWidths=[1.2 * inch, 1 * inch, 1.2 * inch, 2 * inch, 1 * inch])

        # Estilo de tabla
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(table)
        doc.build(elements)

        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="bitacora_{datetime.now().strftime("%Y%m%d")}.pdf"'

        return response

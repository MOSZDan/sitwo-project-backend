from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication, get_authorization_header
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models.fields.related import ForeignKey, OneToOneField
from django.utils.functional import cached_property
import logging

from api.models import Estadodeconsulta, Empresa
from .serializers import EstadodeconsultaSerializer, PoliticaNoShowSerializer
from .models import PoliticaNoShow

logger = logging.getLogger(__name__)

try:
    from rest_framework.authtoken.models import Token  # type: ignore
except Exception:  # pragma: no cover
    Token = None  # type: ignore


class EmpresaFromRequestMixin:
    """
    Resuelve empresa_id (tenant) desde múltiples fuentes.
    Orden:
      1) request.user.empresa_id
      2) request.user.empresa.id
      3) Perfil enlazado: usuario/perfil/profile/userprofile/usuario_perfil/usuario_profile
      4) Búsqueda dinámica de 'Usuario' (api.models.Usuario) por FK a auth user o por email/correoelectronico
      5) Headers: X-Empresa-Id, X-Tenant-Id, X-Empresa, X-Empresa-Name, X-Tenant
      6) Query params: empresa, empresa_id, tenant, tenant_id
      7) Cookies: empresa_id, tenant_id
      8) Si vino Authorization: Token ... pero la auth efectiva fue por sesión, intenta resolver por el token.
    """

    PERFIL_ATTR_CANDIDATES = (
        "usuario",
        "perfil",
        "profile",
        "userprofile",
        "usuario_perfil",
        "usuario_profile",
    )

    HEADER_ID_KEYS = ("X-Empresa-Id", "X-Tenant-Id")
    HEADER_NAME_KEYS = ("X-Empresa", "X-Empresa-Name", "X-Tenant")
    QUERY_ID_KEYS = ("empresa_id", "empresa", "tenant_id", "tenant")
    COOKIE_ID_KEYS = ("empresa_id", "tenant_id")

    def _get_int(self, raw):
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def _normalize_possible_name_to_empresa_id(self, raw_name):
        if not raw_name:
            return None
        if isinstance(raw_name, str) and raw_name.isdigit():
            return self._get_int(raw_name)

        name = str(raw_name).strip()
        # slug
        try:
            if hasattr(Empresa, "slug"):
                obj = Empresa.objects.filter(slug=name).first()
                if obj:
                    return obj.id
        except Exception:
            pass
        # abreviatura
        try:
            if hasattr(Empresa, "abreviatura"):
                obj = Empresa.objects.filter(abreviatura=name).first()
                if obj:
                    return obj.id
        except Exception:
            pass
        # nombre
        try:
            obj = Empresa.objects.filter(nombre__iexact=name).first()
            if obj:
                return obj.id
            obj = Empresa.objects.filter(nombre__icontains=name).first()
            if obj:
                return obj.id
        except Exception:
            pass
        return None

    @cached_property
    def auth_backend_name(self):
        auth = getattr(self.request, "successful_authenticator", None)
        return auth.__class__.__name__ if auth else None

    def _empresa_id_from_user(self, user):
        eid = getattr(user, "empresa_id", None)
        if eid:
            return self._get_int(eid)

        empresa_rel = getattr(user, "empresa", None)
        if empresa_rel and getattr(empresa_rel, "id", None):
            return self._get_int(empresa_rel.id)

        for attr in self.PERFIL_ATTR_CANDIDATES:
            perfil = getattr(user, attr, None)
            if not perfil:
                continue

            eid = getattr(perfil, "empresa_id", None)
            if eid:
                return self._get_int(eid)

            empresa_rel = getattr(perfil, "empresa", None)
            if empresa_rel and getattr(empresa_rel, "id", None):
                return self._get_int(empresa_rel.id)

        # Búsqueda dinámica de api.Usuario
        try:
            from api import models as api_models  # type: ignore
            Usuario = getattr(api_models, "Usuario", None)
        except Exception:
            Usuario = None

        if Usuario:
            # Buscar FK/OneToOne hacia el user actual
            try:
                user_model = user.__class__
                fk_name = None
                for f in Usuario._meta.fields:  # type: ignore
                    if isinstance(f, (ForeignKey, OneToOneField)) and getattr(f, "remote_field", None):
                        if getattr(f.remote_field, "model", None) == user_model:
                            fk_name = f.name
                            break
                if fk_name:
                    perfil = Usuario.objects.filter(**{fk_name: getattr(user, "pk", None)}).first()  # type: ignore
                    if perfil:
                        eid = getattr(perfil, "empresa_id", None)
                        if eid:
                            return self._get_int(eid)
                        empresa_rel = getattr(perfil, "empresa", None)
                        if empresa_rel and getattr(empresa_rel, "id", None):
                            return self._get_int(empresa_rel.id)
            except Exception:
                pass
            # Buscar por email/correo/correoelectronico
            try:
                user_email = getattr(user, "email", None) or getattr(user, "correo", None)
                if user_email:
                    for email_field in ("email", "correo", "correoelectronico"):
                        if hasattr(Usuario, email_field):
                            perfil = Usuario.objects.filter(**{email_field: user_email}).first()  # type: ignore
                            if perfil:
                                eid = getattr(perfil, "empresa_id", None)
                                if eid:
                                    return self._get_int(eid)
                                empresa_rel = getattr(perfil, "empresa", None)
                                if empresa_rel and getattr(empresa_rel, "id", None):
                                    return self._get_int(empresa_rel.id)
                            break
            except Exception:
                pass

        return None

    def _empresa_id_from_headers_qp_cookies(self, req):
        for key in self.HEADER_ID_KEYS:
            raw = req.headers.get(key)
            if raw:
                eid = self._get_int(raw)
                if eid:
                    return eid

        for key in self.HEADER_NAME_KEYS:
            raw = req.headers.get(key)
            if raw:
                eid = self._normalize_possible_name_to_empresa_id(raw)
                if eid:
                    return eid

        for key in self.QUERY_ID_KEYS:
            raw = req.query_params.get(key)
            if raw:
                eid = self._get_int(raw) or self._normalize_possible_name_to_empresa_id(raw)
                if eid:
                    return eid

        for key in self.COOKIE_ID_KEYS:
            raw = req.COOKIES.get(key)
            if raw:
                eid = self._get_int(raw)
                if eid:
                    return eid

        return None

    def _empresa_id_from_token_header(self, req):
        if Token is None:
            return None
        try:
            auth = get_authorization_header(req).decode("utf-8")
        except Exception:
            auth = ""

        if not auth or not auth.strip().lower().startswith("token "):
            return None

        token_key = auth.split(" ", 1)[1].strip()
        if not token_key:
            return None

        try:
            tk = Token.objects.select_related("user").get(key=token_key)  # type: ignore
            return self._empresa_id_from_user(tk.user)  # type: ignore
        except Exception:
            return None

    def empresa_id_from_request(self):
        req = getattr(self, "request", None)
        if not req:
            return None

        # PRIORIDAD 1: request.tenant del TenantMiddleware
        # Esto asegura que el multi-tenancy basado en subdominios se respete
        tenant = getattr(req, "tenant", None)
        if tenant and hasattr(tenant, "id"):
            logger.debug(f"[EmpresaFromRequestMixin] Usando tenant del middleware: {tenant.nombre} (ID: {tenant.id})")
            return tenant.id

        user = getattr(req, "user", None)

        if getattr(user, "is_authenticated", False):
            eid = self._empresa_id_from_user(user)
            if eid:
                return eid

        eid = self._empresa_id_from_headers_qp_cookies(req)
        if eid:
            return eid

        eid = self._empresa_id_from_token_header(req)
        if eid:
            return eid

        return None


class PoliticaNoShowViewSet(EmpresaFromRequestMixin, viewsets.ModelViewSet):
    """
    CRUD de políticas de No-Show por empresa.
    """
    queryset = PoliticaNoShow.objects.all()
    serializer_class = PoliticaNoShowSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        empresa_id = self.empresa_id_from_request()

        logger.info(
            "PoliticaNoShowViewSet empresa_id=%s user_id=%s super=%s auth=%s header_tenant=%s qp=%s",
            empresa_id,
            getattr(self.request.user, "id", None),
            getattr(self.request.user, "is_superuser", None),
            self.auth_backend_name,
            self.request.headers.get("X-Empresa-Id") or self.request.headers.get("X-Tenant-Id") or self.request.headers.get("X-Tenant"),
            dict(self.request.query_params),
        )

        if not empresa_id:
            return PoliticaNoShow.objects.none()
        return PoliticaNoShow.objects.filter(empresa_id=empresa_id).order_by("id")

    def perform_create(self, serializer):
        empresa_id = self.empresa_id_from_request()
        if not empresa_id:
            logger.warning("PoliticaNoShowViewSet.perform_create: empresa_id no detectada. auth=%s user_id=%s",
                           self.auth_backend_name, getattr(self.request.user, "id", None))
            self._bad_request_no_empresa = True
            return

        empresa = get_object_or_404(Empresa, pk=empresa_id)
        serializer.save(empresa=empresa)

    def create(self, request, *args, **kwargs):
        self._bad_request_no_empresa = False
        response = super().create(request, *args, **kwargs)
        if getattr(self, "_bad_request_no_empresa", False):
            return Response({"detail": "No se pudo determinar la empresa del usuario."}, status=status.HTTP_400_BAD_REQUEST)
        return response


class EstadodeconsultaViewSet(EmpresaFromRequestMixin, viewsets.ReadOnlyModelViewSet):
    """
    Lista los estados de consulta filtrando SIEMPRE por empresa del usuario.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = EstadodeconsultaSerializer

    def get_queryset(self):
        empresa_id = self.empresa_id_from_request()

        logger.info(
            "EstadodeconsultaViewSet empresa_id detectada=%s, user_id=%s, super=%s, auth=%s, headers[X-*]=%s, qp=%s",
            empresa_id,
            getattr(self.request.user, "id", None),
            getattr(self.request.user, "is_superuser", None),
            self.auth_backend_name,
            {
                "X-Empresa-Id": self.request.headers.get("X-Empresa-Id"),
                "X-Tenant-Id": self.request.headers.get("X-Tenant-Id"),
                "X-Tenant": self.request.headers.get("X-Tenant"),
                "X-Empresa": self.request.headers.get("X-Empresa"),
                "X-Empresa-Name": self.request.headers.get("X-Empresa-Name"),
            },
            dict(self.request.query_params),
        )

        if not empresa_id:
            # Si prefieres que el superuser vea todo, descomenta:
            # if getattr(self.request.user, "is_superuser", False):
            #     return Estadodeconsulta.objects.all().order_by("estado")
            return Estadodeconsulta.objects.none()

        return Estadodeconsulta.objects.filter(empresa_id=empresa_id).order_by("estado")
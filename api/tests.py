# api/tests.py
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Paciente, Horario, Tipodeconsulta, Estadodeconsulta, Usuario, Tipodeusuario

User = get_user_model()


class ConsultaAPITestCase(APITestCase):

    def setUp(self):
        """Crea los datos iniciales necesarios para cada prueba."""
        self.user = User.objects.create_user(username='test@test.com', password='testpassword123')
        self.client.force_authenticate(user=self.user)

        self.tipo_usuario = Tipodeusuario.objects.create(rol='paciente')
        self.horario = Horario.objects.create(hora="10:00:00")
        self.tipo_consulta = Tipodeconsulta.objects.create(nombreconsulta="Limpieza General")
        self.estado_consulta = Estadodeconsulta.objects.create(estado="Agendada")

        self.usuario_paciente = Usuario.objects.create(
            nombre="Juan",
            apellido="Perez",
            correoelectronico="juan@perez.com",
            idtipousuario=self.tipo_usuario
        )
        self.paciente = Paciente.objects.create(codusuario=self.usuario_paciente)

    def test_create_consulta_success(self):
        """Prueba que se puede crear una consulta exitosamente."""
        url = '/api/consultas/'
        data = {
            "fecha": "2025-11-10",
            "codpaciente": self.paciente.codusuario_id,
            "idhorario": self.horario.id,
            "idtipoconsulta": self.tipo_consulta.id,
            "idestadoconsulta": self.estado_consulta.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['fecha'], '2025-11-10')

    def test_create_consulta_missing_data(self):
        """Prueba que la creación falla si faltan datos requeridos."""
        url = '/api/consultas/'
        data = {"fecha": "2025-11-11"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

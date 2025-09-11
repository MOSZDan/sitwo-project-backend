from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Paciente, Tipodeusuario

User = get_user_model()

class AuthTests(APITestCase):

    def setUp(self):
        # Creamos los tipos de usuario necesarios antes de cada prueba
        Tipodeusuario.objects.create(id=1, rol='Administrador')
        Tipodeusuario.objects.create(id=2, rol='Paciente')
        Tipodeusuario.objects.create(id=3, rol='Odontologo')
        Tipodeusuario.objects.create(id=4, rol='Recepcionista')

    def test_registro_paciente_exitoso(self):
        """
        Prueba que un nuevo paciente puede registrarse correctamente.
        """
        # Datos que enviaría el frontend
        data = {
            "email": "nuevo.paciente@example.com",
            "password": "passwordSeguro123",
            "nombre": "Juan",
            "apellido": "Perez",
            "telefono": "77712345",
            "sexo": "Masculino",
            "rol": "paciente",
            "carnetidentidad": "12345678",
            "fechanacimiento": "1990-01-15",
            "direccion": "Calle Falsa 123"
        }

        # Hacemos la petición POST a la URL de registro
        url = "/api/auth/register/"
        response = self.client.post(url, data, format='json')

        # 1. Verificamos que la respuesta sea exitosa (HTTP 201 CREATED)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 2. Verificamos que el usuario se haya creado en la base de datos
        self.assertTrue(User.objects.filter(email="nuevo.paciente@example.com").exists())

        # 3. Verificamos que el paciente se haya creado
        self.assertTrue(Paciente.objects.filter(carnetidentidad="12345678").exists())

        # 4. Verificamos que la respuesta JSON contenga los datos esperados
        self.assertEqual(response.data['user']['email'], 'nuevo.paciente@example.com')
        self.assertEqual(response.data['subtipo'], 'paciente')

    def test_registro_email_duplicado(self):
        """
        Prueba que no se puede registrar un usuario con un email que ya existe.
        """
        # Primero, creamos un usuario para que el email ya exista
        User.objects.create_user(username='existente@example.com', email='existente@example.com', password='password1')

        data = {
            "email": "existente@example.com",
            "password": "passwordSeguro123",
            "nombre": "Ana",
            "apellido": "Gomez",
            "telefono": "77754321",
            "sexo": "Femenino",
            "rol": "paciente",
            "carnetidentidad": "87654321",
            "fechanacimiento": "1995-05-20",
            "direccion": "Avenida Siempre Viva 742"
        }

        url = "/api/auth/register/"
        response = self.client.post(url, data, format='json')

        # Verificamos que la respuesta sea un conflicto (HTTP 409 CONFLICT)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['detail'], 'Ya existe un usuario con ese email.')
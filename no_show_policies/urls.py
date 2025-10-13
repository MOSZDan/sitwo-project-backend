from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PoliticaNoShowViewSet, EstadodeconsultaViewSet

router = DefaultRouter()
router.register(r'politicas-no-show', PoliticaNoShowViewSet, basename='politicas-no-show')
router.register(r'estadodeconsultas', EstadodeconsultaViewSet, basename='estadodeconsultas')

urlpatterns = [
    path('', include(router.urls)),
]
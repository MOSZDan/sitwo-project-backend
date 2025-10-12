# api/notifications_mobile/urls.py
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from .views import (
    MobileRegisterDeviceView,
    MobileRegisterDeviceLiteView,
    MobileNotificationsHealthView,
    MobileNotificationsTestPushView,
    mobile_dispatch_notification,
    mobile_dispatch_due,
)

urlpatterns = [
    # Exentos de CSRF porque se consumen con Authorization: Token desde app móvil
    path('register-device/', csrf_exempt(MobileRegisterDeviceView.as_view()), name='mobile-register-device'),
    path('register-lite/', csrf_exempt(MobileRegisterDeviceLiteView.as_view()), name='mobile-register-device-lite'),
    path('dispatch/<int:pk>/', mobile_dispatch_notification, name='mobile-dispatch'),
    path('dispatch-due/', mobile_dispatch_due, name='mobile-dispatch-due'),

    # Estos pueden quedar sin exención si quieres
    path('health/', MobileNotificationsHealthView.as_view(), name='mobile-notif-health'),
    path('test-push/', MobileNotificationsTestPushView.as_view(), name='mobile-notif-test-push'),
]

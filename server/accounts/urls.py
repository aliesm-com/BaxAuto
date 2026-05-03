from django.urls import include, path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenBlacklistView, TokenRefreshView, TokenVerifyView

from .views import AdminUserViewSet, ChangePasswordView, CustomTokenObtainPairView, MeView

router = SimpleRouter()
router.register('users', AdminUserViewSet, basename='account-user')

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='jwt-login'),
    path('refresh/', TokenRefreshView.as_view(), name='jwt-refresh'),
    path('logout/', TokenBlacklistView.as_view(), name='jwt-logout'),
    path('verify/', TokenVerifyView.as_view(), name='jwt-verify'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('me/change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('', include(router.urls)),
]

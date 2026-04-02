# DRF Routers configuration
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

# Register your viewsets here
# Example:
# router.register(r'users', UserViewSet, basename='user')

app_name = 'api'
urlpatterns = router.urls

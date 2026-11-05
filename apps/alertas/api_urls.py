from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register("alertas", api.AlertaViewSet)

urlpatterns = router.urls

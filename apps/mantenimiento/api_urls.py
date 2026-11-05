from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register("mantenimientos", api.MantenimientoViewSet)
router.register("planes-mantenimiento", api.PlanViewSet)

urlpatterns = router.urls

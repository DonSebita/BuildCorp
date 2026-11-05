from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register("categorias", api.CategoriaViewSet)
router.register("bodegas", api.BodegaViewSet)
router.register("activos", api.ActivoViewSet)
router.register("paquetes", api.PaqueteViewSet)

urlpatterns = router.urls

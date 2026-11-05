from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register("contratistas", api.ContratistaViewSet)
router.register("obras", api.ObraViewSet)

urlpatterns = router.urls

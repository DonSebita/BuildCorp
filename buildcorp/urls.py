from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "BuildCorp – Administración"
admin.site.site_title = "BuildCorp"
admin.site.index_title = "Panel de administración"

api_v1 = [
    path("", include("apps.activos.api_urls")),
    path("", include("apps.contratistas.api_urls")),
    path("", include("apps.prestamos.api_urls")),
    path("", include("apps.mantenimiento.api_urls")),
    path("", include("apps.alertas.api_urls")),
    path("", include("apps.dashboard.api_urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("", include("apps.usuarios.urls")),
    path("", include("apps.dashboard.urls")),
    path("activos/", include("apps.activos.urls")),
    path("contratistas/", include("apps.contratistas.urls")),
    path("prestamos/", include("apps.prestamos.urls")),
    path("mantenimiento/", include("apps.mantenimiento.urls")),
    path("alertas/", include("apps.alertas.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

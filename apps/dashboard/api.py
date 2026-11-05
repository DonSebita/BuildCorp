from rest_framework.response import Response
from rest_framework.views import APIView

from .services import resumen


class ResumenView(APIView):
    """KPIs, gráfico, tablas y alertas del dashboard según el rol del usuario."""

    def get(self, request):
        return Response(resumen(request.user))

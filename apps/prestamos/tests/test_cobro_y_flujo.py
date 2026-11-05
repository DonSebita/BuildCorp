import base64
import io
from datetime import timedelta

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from PIL import Image, ImageDraw
from rest_framework.test import APIClient

from apps.activos.models import Activo, CategoriaActivo, ItemPaquete, PaqueteMaquinaria
from apps.activos.services import crear_activo
from apps.contratistas.models import Contratista, Obra
from apps.prestamos import services
from apps.prestamos.models import Prestamo
from apps.usuarios.models import Usuario
from apps.usuarios.roles import ENCARGADO, TODOS, VENTAS


def firma():
    img = Image.new("RGBA", (300, 100), (0, 0, 0, 0))
    ImageDraw.Draw(img).line([(10, 50), (290, 60)], fill=(0, 0, 0, 255), width=4)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return {"nombre": "Luis Herrera", "rut": "12.345.678-9", "imagen": base64.b64encode(buf.getvalue()).decode()}


class CalculoCLPTests(TestCase):
    def test_menos_de_30_dias(self):
        self.assertEqual(services.calcular_arriendo(12, 15000, 300000), 180000)

    def test_ejemplo_de_la_planificacion_45_dias(self):
        # 1 × $300.000 + min(15 × $15.000, $300.000) = $525.000
        self.assertEqual(services.calcular_arriendo(45, 15000, 300000), 525000)

    def test_resto_no_supera_un_mes(self):
        self.assertEqual(services.calcular_arriendo(59, 15000, 300000), 600000)

    def test_minimo_un_dia(self):
        hoy = timezone.localdate()
        self.assertEqual(services.dias_entre(hoy, hoy), 1)


class FlujoArriendoTests(TestCase):
    def setUp(self):
        for rol in TODOS:
            Group.objects.create(name=rol)
        self.ventas = Usuario.objects.create_user("ventas", password="x")
        self.ventas.groups.add(Group.objects.get(name=VENTAS))
        self.encargado = Usuario.objects.create_user("encargado", password="x")
        self.encargado.groups.add(Group.objects.get(name=ENCARGADO))
        self.cat = CategoriaActivo.objects.create(nombre="Rotomartillo", prefijo_codigo="RTM", tarifa_diaria=15000,
                                                  tarifa_mensual=300000, mant_cada_usos=2)
        self.a1 = crear_activo(self.ventas, categoria=self.cat, nombre="Rotomartillo")
        self.a2 = crear_activo(self.ventas, categoria=self.cat, nombre="Rotomartillo")
        self.c = Contratista.objects.create(rut="1-9", razon_social="Andes Sur")
        self.obra = Obra.objects.create(nombre="Los Robles", contratista=self.c, responsable_nombre="Luis", responsable_rut="1-9")
        self.paquete = PaqueteMaquinaria.objects.create(codigo="PAQ", nombre="Kit", tarifa_diaria=25000, tarifa_mensual=500000)
        ItemPaquete.objects.create(paquete=self.paquete, categoria=self.cat, cantidad=1)

    def test_codigo_correlativo_inmutable(self):
        self.assertEqual([self.a1.codigo, self.a2.codigo], ["RTM-0001", "RTM-0002"])

    def test_ciclo_completo_por_api(self):
        hoy = timezone.localdate()
        api = APIClient()
        api.force_authenticate(self.ventas)
        r = api.post("/api/v1/prestamos/", {
            "contratista": self.c.pk, "obra": self.obra.pk, "fecha_entrega": hoy.isoformat(),
            "fecha_devolucion_pactada": (hoy + timedelta(days=5)).isoformat(), "paquetes": [self.paquete.pk],
        }, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        pid, pp = r.data["id"], r.data["paquetes"][0]["id"]

        # Ventas no puede entregar (separación de funciones)
        self.assertEqual(api.post(f"/api/v1/prestamos/{pid}/entregar/", {"firma": firma()}, format="json").status_code, 403)

        api.force_authenticate(self.encargado)
        r = api.post(f"/api/v1/prestamos/{pid}/asignar-activos/", {"prestamo_paquete": pp, "codigos": ["RTM-0001"]}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        r = api.post(f"/api/v1/prestamos/{pid}/entregar/", {"checklist": {}, "firma": firma()}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.estado, Activo.Estado.EN_USO)

        r = api.post(f"/api/v1/prestamos/{pid}/devolver/", {"recepcion": {}, "firma": firma()}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        p = Prestamo.objects.get(pk=pid)
        self.assertEqual(p.estado, Prestamo.Estado.DEVUELTO)
        self.assertEqual(p.cobro.monto_arriendo, 25000)  # 1 día × tarifa del paquete
        self.assertEqual(p.cobro.total, 25000 + round(25000 * 0.19))
        self.assertEqual(p.firmas.count(), 2)

    def test_umbral_de_usos_pasa_a_mantenimiento(self):
        Activo.objects.filter(pk=self.a1.pk).update(usos_desde_mantencion=1)
        hoy = timezone.localdate()
        p = services.crear_prestamo(self.ventas, self.c, self.obra, hoy, hoy, activos=[self.a1])
        services.entregar(p, self.encargado, {}, firma())
        services.devolver(p, self.encargado, {}, firma())
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.estado, Activo.Estado.MANTENIMIENTO)

    def test_morosidad_bloquea_y_no_permite_prestar(self):
        hoy = timezone.localdate()
        p = services.crear_prestamo(self.ventas, self.c, self.obra, hoy - timedelta(days=10), hoy - timedelta(days=5),
                                    activos=[self.a1])
        services.entregar(p, self.encargado, {}, firma())
        resumen = services.revisar_morosidad()
        self.c.refresh_from_db()
        self.assertEqual(resumen["bloqueados"], 1)
        self.assertTrue(self.c.bloqueado)
        with self.assertRaises(ValidationError):
            services.crear_prestamo(self.ventas, self.c, self.obra, hoy, hoy, activos=[self.a2])

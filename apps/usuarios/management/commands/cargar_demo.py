"""Datos de demostración: usuarios por rol, bodegas, categorías, ~34 activos, paquetes,
contratistas (uno activo, uno con atraso y uno bloqueado), préstamos con firmas y mantenciones."""
import base64
import io
import math
from datetime import datetime, time, timedelta

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from apps.activos import services as activos_srv
from apps.activos.models import Activo, Bodega, CategoriaActivo, HistorialEstado, ItemPaquete, PaqueteMaquinaria
from apps.contratistas.models import Contratista, Obra
from apps.mantenimiento import services as mant_srv
from apps.mantenimiento.models import Mantenimiento
from apps.prestamos import services as prest_srv
from apps.prestamos.models import Cobro, Firma, ParametroSistema, Prestamo
from apps.usuarios.models import Usuario
from apps.usuarios.roles import ADMIN, BODEGUERO, ENCARGADO, VENTAS

CLAVE_DEMO = "buildcorp2026"

CATEGORIAS = [
    # nombre, prefijo, diaria, mensual, horómetro, usos, horas, días, cantidad, marcas
    ("Taladro percutor", "TAL", 8000, 160000, False, 15, None, 180, 4, ["Bosch GSB 18V", "Makita HP2050"]),
    ("Esmeril angular", "ESM", 7000, 140000, False, 15, None, 180, 3, ["DeWalt DWE4120", "Bosch GWS 900"]),
    ("Lijadora orbital", "LIJ", 6000, 120000, False, 15, None, 180, 2, ["Makita BO5031"]),
    ("Sierra circular", "SIE", 9000, 180000, False, 15, None, 180, 2, ["Makita 5007N"]),
    ("Rotomartillo", "RTM", 15000, 300000, False, 10, None, 120, 5, ["Hilti TE 30", "Bosch GBH 2-28"]),
    ("Demoledor", "DEM", 25000, 500000, False, 10, None, 120, 2, ["Hilti TE 1000", "Makita HM1307"]),
    ("Generador", "GEN", 30000, 600000, True, 8, 200, 90, 3, ["Honda EU30is", "Kipor KDE6500"]),
    ("Placa compactadora", "CMP", 28000, 560000, True, 8, 200, 90, 2, ["Wacker Neuson VP1550"]),
    ("Canguro compactador", "CAN", 30000, 600000, True, 8, 200, 90, 1, ["Wacker Neuson BS60-4"]),
    ("Betonera", "BET", 22000, 440000, True, 8, 200, 90, 2, ["Imer Syntesi 350"]),
    ("Vibrador de inmersión", "VIB", 12000, 240000, True, 8, 200, 90, 2, ["Wacker Neuson M2500"]),
    ("Motobomba", "MTB", 18000, 360000, True, 8, 200, 90, 2, ["Honda WB30"]),
    ("Andamio (cuerpo)", "AND", 3000, 60000, False, 20, None, 180, 4, ["Layher Allround"]),
]

PAQUETES = [
    ("PAQ-OG", "Kit Obra Gruesa", 85000, 1600000, {"BET": 1, "VIB": 1, "RTM": 2, "GEN": 1}),
    ("PAQ-DM", "Kit Demolición", 70000, 1300000, {"DEM": 1, "RTM": 1, "ESM": 1, "GEN": 1}),
    ("PAQ-TE", "Kit Terminaciones", 35000, 650000, {"TAL": 2, "LIJ": 1, "SIE": 1, "ESM": 1}),
    ("PAQ-CP", "Kit Compactación", 60000, 1100000, {"CMP": 1, "CAN": 1, "MTB": 1}),
]


def firma_png(semilla):
    """Firma de ejemplo dibujada con Pillow (PNG en base64)."""
    img = Image.new("RGBA", (600, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    puntos = [(60 + x, 110 + 38 * math.sin(x / (18 + semilla)) * math.cos(x / (41 + semilla * 3))) for x in range(0, 470, 4)]
    d.line(puntos, fill=(29, 27, 58, 255), width=4, joint="curve")
    d.line([(90, 150), (520, 138)], fill=(29, 27, 58, 255), width=3)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class Command(BaseCommand):
    help = "Carga datos de demostración (usa --reset para borrar los datos de negocio antes)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Borra préstamos, activos y contratistas antes de cargar.")

    def handle(self, *args, **opts):
        if opts["reset"]:
            self.borrar()
        elif Activo.objects.exists():
            self.stdout.write(self.style.WARNING("Ya hay datos. Usa --reset para recargar la demo."))
            return
        call_command("cargar_roles", verbosity=0)
        with transaction.atomic():
            self.hoy = timezone.localdate()
            self.usuarios()
            ParametroSistema.objects.update_or_create(pk=1, defaults={"dias_gracia": 3, "recargo_atraso": 0.5, "tasa_iva": 0.19})
            self.inventario()
            self.contratistas()
            self.prestamos()
            self.mantenciones()
        call_command("revisar_mantenimientos", verbosity=0)
        call_command("revisar_morosidad", verbosity=0)
        self.stdout.write(self.style.SUCCESS(
            f"Demo cargada. Usuarios: admin, bodeguero, encargado, ventas · contraseña «{CLAVE_DEMO}»."
        ))

    # ------------------------------------------------------------------ helpers
    def borrar(self):
        from apps.alertas.models import Alerta

        Alerta.objects.all().delete()
        Cobro.objects.all().delete()
        Prestamo.objects.all().delete()  # cascada a detalles, firmas
        Mantenimiento.objects.all().delete()
        Activo.objects.all().delete()
        PaqueteMaquinaria.objects.all().delete()
        CategoriaActivo.objects.all().delete()
        Bodega.objects.all().delete()
        Contratista.objects.all().delete()

    def momento(self, dias_atras, hora=10):
        return timezone.make_aware(datetime.combine(self.hoy - timedelta(days=dias_atras), time(hora, 0)))

    def usuarios(self):
        datos = [
            ("admin", "Patricia", "Soto Lagos", ADMIN, "Gerente de operaciones", True),
            ("bodeguero", "Jorge", "Muñoz Vera", BODEGUERO, "Jefe de bodega", False),
            ("encargado", "Rodrigo", "Pérez Fuentes", ENCARGADO, "Inspector de entrega y recepción", False),
            ("ventas", "Camila", "Rojas Díaz", VENTAS, "Ejecutiva comercial", False),
        ]
        self.u = {}
        for username, nombre, apellido, rol, cargo, staff in datos:
            u, _ = Usuario.objects.get_or_create(username=username)
            u.first_name, u.last_name, u.cargo = nombre, apellido, cargo
            u.email = f"{username}@buildcorp.cl"
            u.is_staff = u.is_superuser = staff
            u.set_password(CLAVE_DEMO)
            u.save()
            u.groups.set([Group.objects.get(name=rol)])
            self.u[username] = u

    def inventario(self):
        self.central = Bodega.objects.create(nombre="Bodega Central", tipo="CENTRAL",
                                             direccion="Av. Américo Vespucio 1450, Quilicura", encargado=self.u["bodeguero"])
        self.norte = Bodega.objects.create(nombre="Bodega Obra Norte", tipo="OBRA",
                                           direccion="Camino Lo Boza 120, Pudahuel", encargado=self.u["bodeguero"])
        self.cat = {}
        serie = 3000
        for nombre, pref, diaria, mensual, horo, usos, horas, dias, cantidad, modelos in CATEGORIAS:
            c = CategoriaActivo.objects.create(
                nombre=nombre, prefijo_codigo=pref, tarifa_diaria=diaria, tarifa_mensual=mensual,
                requiere_horometro=horo, mant_cada_usos=usos, mant_cada_horas=horas, mant_cada_dias=dias,
            )
            self.cat[pref] = c
            for i in range(cantidad):
                marca, modelo = modelos[i % len(modelos)].split(" ", 1)
                serie += 137
                a = activos_srv.crear_activo(
                    self.u["bodeguero"], categoria=c, nombre=nombre, marca=marca, modelo=modelo,
                    numero_serie=f"SN-{pref}{serie}-{'ABC'[i % 3]}",
                    fecha_adquisicion=self.hoy - timedelta(days=420 + i * 30),
                    valor_compra=diaria * 45, bodega_actual=self.norte if i == cantidad - 1 and cantidad > 2 else self.central,
                )
                HistorialEstado.objects.filter(activo=a).update(fecha=self.momento(200 + i))
                a.plan.ultima_fecha = self.hoy - timedelta(days=40 + i * 7)
                a.plan.save()
        for cod, nombre, diaria, mensual, items in PAQUETES:
            p = PaqueteMaquinaria.objects.create(codigo=cod, nombre=nombre, tarifa_diaria=diaria, tarifa_mensual=mensual,
                                                 creado_por=self.u["ventas"],
                                                 descripcion=f"Paquete referencial para la demo: {nombre.lower()}.")
            for pref, n in items.items():
                ItemPaquete.objects.create(paquete=p, categoria=self.cat[pref], cantidad=n)
        self.paq = {p.codigo: p for p in PaqueteMaquinaria.objects.all()}

    def contratistas(self):
        self.andes = Contratista.objects.create(rut="76.123.456-7", razon_social="Constructora Andes Sur SpA",
                                                contacto="Marcela Ortiz", email="compras@andessur.cl", telefono="+56 2 2345 6789")
        self.pacifico = Contratista.objects.create(rut="77.654.321-K", razon_social="Montajes Pacífico Ltda.",
                                                   contacto="Felipe Araya", email="faraya@montajespacifico.cl", telefono="+56 9 8765 4321")
        self.cordillera = Contratista.objects.create(rut="78.222.333-4", razon_social="Ingeniería Cordillera SpA",
                                                     contacto="Daniela Reyes", email="dreyes@icordillera.cl", telefono="+56 9 5555 1212")
        self.o_robles = Obra.objects.create(nombre="Edificio Los Robles", direccion="Los Robles 2350, Ñuñoa", contratista=self.andes,
                                            responsable_nombre="Luis Herrera", responsable_rut="12.345.678-9",
                                            fecha_inicio=self.hoy - timedelta(days=120))
        self.o_maiten = Obra.objects.create(nombre="Condominio El Maitén", direccion="Camino El Maitén 455, Colina", contratista=self.andes,
                                            responsable_nombre="Paula Castro", responsable_rut="15.678.901-2",
                                            fecha_inicio=self.hoy - timedelta(days=60))
        self.o_quilicura = Obra.objects.create(nombre="Galpón Quilicura", direccion="Lo Echevers 900, Quilicura",
                                               contratista=self.pacifico, responsable_nombre="Héctor Salinas",
                                               responsable_rut="10.987.654-3", fecha_inicio=self.hoy - timedelta(days=90))
        self.o_ruta = Obra.objects.create(nombre="Paso superior Ruta 68", direccion="Ruta 68 km 14, Pudahuel",
                                          contratista=self.cordillera, responsable_nombre="Andrea Vidal",
                                          responsable_rut="16.111.222-3", fecha_inicio=self.hoy - timedelta(days=150))

    def libres(self, pref, n):
        return list(Activo.objects.filter(categoria=self.cat[pref], estado="DISPONIBLE").order_by("codigo")[:n])

    def ciclo(self, contratista, obra, salida, pactado, paquetes=(), sueltos=(), vuelta=None, danos=None, pagar=False,
              entregar=True):
        """Crea, entrega y (opcionalmente) devuelve un préstamo con fechas en el pasado.
        salida / pactado / vuelta: días relativos a hoy (negativo = pasado)."""
        f_salida = self.hoy + timedelta(days=salida)
        p = prest_srv.crear_prestamo(
            self.u["ventas"], contratista, obra, f_salida, self.hoy + timedelta(days=pactado),
            paquetes=[self.paq[c] for c in paquetes], activos=sueltos,
        )
        Prestamo.objects.filter(pk=p.pk).update(creado=self.momento(max(1, -salida + 1), 16))
        if not entregar:
            return p  # queda por entregar; el encargado asigna los equipos escaneándolos
        for pp in p.paquetes.all():
            codigos = [a.codigo for pref_cat, n in ((i.categoria.prefijo_codigo, i.cantidad) for i in pp.paquete.items.all())
                       for a in self.libres(pref_cat, n)]
            prest_srv.asignar_activos(p, pp, codigos)
        checklist = {
            str(d.pk): {"estado_salida": "BUENO", "horometro_salida": str(d.activo.horas_uso_totales) if d.activo.categoria.requiere_horometro else None}
            for d in p.detalles.select_related("activo__categoria")
        }
        prest_srv.entregar(p, self.u["encargado"], checklist,
                           {"nombre": obra.responsable_nombre, "rut": obra.responsable_rut, "imagen": firma_png(p.pk % 5)}, "10.0.0.15")
        Prestamo.objects.filter(pk=p.pk).update(fecha_entrega=f_salida)
        HistorialEstado.objects.filter(referencia=p.codigo, estado_nuevo="EN_USO").update(fecha=self.momento(-salida, 9))
        Firma.objects.filter(prestamo=p, tipo="ENTREGA").update(fecha=self.momento(-salida, 9))
        if vuelta is None:
            return p
        danos = danos or {}
        recepcion = {}
        for d in p.detalles.select_related("activo__categoria"):
            r = {"estado_llegada": "BUENO"}
            if d.activo.categoria.requiere_horometro:
                r["horometro_llegada"] = float(d.horometro_salida or 0) + 2.5 * (vuelta - salida)
            if d.activo.codigo in danos:
                r.update(estado_llegada="DANADO", observacion_dano=danos[d.activo.codigo][0], cargo_dano=danos[d.activo.codigo][1])
            recepcion[str(d.pk)] = r
        p.refresh_from_db()
        prest_srv.devolver(p, self.u["encargado"], recepcion,
                           {"nombre": obra.responsable_nombre, "rut": obra.responsable_rut, "imagen": firma_png(p.pk % 5 + 1)},
                           "10.0.0.15", fecha=self.hoy + timedelta(days=vuelta))
        HistorialEstado.objects.filter(referencia=p.codigo).exclude(estado_nuevo="EN_USO").update(fecha=self.momento(-vuelta, 17))
        Firma.objects.filter(prestamo=p, tipo="DEVOLUCION").update(fecha=self.momento(-vuelta, 17))
        if pagar:
            prest_srv.registrar_pago(p.cobro, self.u["ventas"], fecha=self.hoy + timedelta(days=vuelta + 6))
        return p

    def prestamos(self):
        # Historial cerrado y pagado
        self.ciclo(self.andes, self.o_robles, -150, -138, paquetes=["PAQ-TE"], vuelta=-137, pagar=True)
        self.ciclo(self.andes, self.o_robles, -130, -95, paquetes=["PAQ-OG"], vuelta=-93, pagar=True)
        self.ciclo(self.pacifico, self.o_quilicura, -110, -100, paquetes=["PAQ-CP"], vuelta=-100, pagar=True)
        self.ciclo(self.andes, self.o_maiten, -80, -66, paquetes=["PAQ-DM"], vuelta=-66, pagar=True)
        self.ciclo(self.cordillera, self.o_ruta, -70, -40, sueltos=self.libres("RTM", 2) + self.libres("AND", 4), vuelta=-38, pagar=True)
        self.ciclo(self.pacifico, self.o_quilicura, -45, -30, paquetes=["PAQ-TE"], vuelta=-29, pagar=True)
        # Devueltos con cobro pendiente (uno con daño)
        rtm = self.libres("RTM", 1)
        self.ciclo(self.pacifico, self.o_quilicura, -25, -12, sueltos=rtm + self.libres("ESM", 1), vuelta=-11,
                   danos={rtm[0].codigo: ("Mandril trizado, no sujeta la broca", 45000)})
        self.ciclo(self.andes, self.o_maiten, -20, -6, paquetes=["PAQ-TE"], vuelta=-5)
        # En terreno: atrasado más allá de la gracia (bloquea a Cordillera), atrasado dentro de la gracia y al día
        self.ciclo(self.cordillera, self.o_ruta, -40, -9, paquetes=["PAQ-DM"])
        self.ciclo(self.pacifico, self.o_quilicura, -12, -2, sueltos=self.libres("TAL", 1) + self.libres("SIE", 1))
        self.ciclo(self.andes, self.o_robles, -6, 0, paquetes=["PAQ-OG"])
        self.ciclo(self.andes, self.o_maiten, -3, 2, sueltos=self.libres("AND", 2))
        # Por entregar (Encargado E/R)
        self.ciclo(self.andes, self.o_maiten, 0, 14, paquetes=["PAQ-CP"], entregar=False)
        self.ciclo(self.pacifico, self.o_quilicura, 1, 8, sueltos=self.libres("LIJ", 1) + self.libres("ESM", 1), entregar=False)

    def mantenciones(self):
        # Mantenciones históricas con folio
        for codigo, dias, tecnico, costo, texto in [
            ("GEN-0001", 60, "Servicio Técnico Honda Santiago", 85000, "Cambio de aceite, bujía y filtro de aire."),
            ("RTM-0002", 45, "Taller BuildCorp", 32000, "Cambio de carbones y lubricación del percutor."),
            ("CMP-0001", 30, "Wacker Neuson Chile", 120000, "Cambio de correa y revisión de placa base."),
        ]:
            a = Activo.objects.get(codigo=codigo)
            if a.estado != "DISPONIBLE":
                continue
            m = mant_srv.registrar_mantenimiento(a, self.u["bodeguero"], tipo="PREVENTIVO", estado="FINALIZADA",
                                                 fecha=self.hoy - timedelta(days=dias), tecnico=tecnico, costo=costo, descripcion=texto)
            HistorialEstado.objects.filter(referencia=m.folio).update(fecha=self.momento(dias, 15))
        # Próximas y vencidas: usos acumulados y fechas límite
        ajustes = {"TAL-0004": 14, "ESM-0003": 13, "AND-0004": 19, "SIE-0002": 15}
        for codigo, usos in ajustes.items():
            Activo.objects.filter(codigo=codigo).update(usos_desde_mantencion=usos, usos_totales=usos + 12)
        for codigo, dias in {"GEN-0003": 95, "BET-0002": 86, "MTB-0002": 88}.items():
            a = Activo.objects.get(codigo=codigo)
            a.plan.ultima_fecha = self.hoy - timedelta(days=dias)
            a.plan.save()
        # Un equipo en taller con mantención correctiva abierta
        a = Activo.objects.get(codigo="DEM-0002")
        if a.estado == "DISPONIBLE":
            m = mant_srv.registrar_mantenimiento(a, self.u["bodeguero"], tipo="CORRECTIVO", estado="EN_CURSO",
                                                 fecha=self.hoy - timedelta(days=2), tecnico="Hilti Service Center",
                                                 costo=0, descripcion="Pierde potencia de impacto. En diagnóstico.")
            HistorialEstado.objects.filter(referencia=m.folio).update(fecha=self.momento(2, 11))

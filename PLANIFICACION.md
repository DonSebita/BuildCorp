# BuildCorp: Planificación del proyecto

**Sistema interno de alquiler y control de herramientas y maquinaria ligera**

> Este documento sirve de guía para desarrollar el proyecto. Define el alcance, los roles, el modelo de datos, la arquitectura, la estructura del repositorio y las fases de trabajo.
> **No es una tienda en línea.** Es un software interno: solo usa la aplicación el personal de BuildCorp. Los contratistas y subcontratistas **no tienen cuenta**. Se registran como entidades, y el responsable de obra firma digitalmente en el dispositivo del encargado al momento de la entrega y de la devolución.

---

## 1. Contexto y objetivo

| Aspecto | Detalle |
|---|---|
| Problema | Pérdida de maquinaria y herramientas, cobros inexactos a subcontratistas y fallas mecánicas imprevistas. Además, no se ve el inventario repartido entre varias obras. |
| Objetivo | Un sistema centralizado que controle préstamos, trazabilidad entre bodegas de obra, hojas de vida de equipos y mantenimiento preventivo. |
| Usuarios | Personal interno: administrador, bodeguero, encargado de entrega/recepción y ventas. |

### Requerimientos funcionales del caso

| # | Requerimiento | Módulo |
|---|---|---|
| RF1 | Catálogo de activos con trazabilidad de estado (Disponible, En Uso, Mantenimiento, Dado de Baja) | `activos` |
| RF2 | Entrega y devolución con firma digital del responsable de obra | `prestamos` |
| RF3 | Mantenimientos preventivos según horas de uso o fecha límite | `mantenimiento` |
| RF4 | Alertas por morosidad en devoluciones y bloqueo automático de contratistas morosos | `contratistas` + `alertas` |

### Requerimientos técnicos

| # | Requerimiento |
|---|---|
| RT1 | Django + Django REST Framework (DRF) |
| RT2 | Django Admin habilitado y **personalizado** para los modelos del dominio |
| RT3 | Sesiones, autenticación y permisos por rol |
| RT4 | PostgreSQL y migraciones del ORM aplicadas correctamente |
| RT5 | Frontend responsivo con templates HTML/CSS/JS y llamadas asíncronas (fetch) a la API |
| RT6 | Despliegue en **una sola instancia EC2** (AWS Academy), con Django y PostgreSQL en la misma instancia y acceso público por IP o DNS |
| RT7 | `README.md` con instrucciones y la IP pública, y `prompts_ia.md` con el registro de uso de IA |

---

## 2. Roles y permisos

Los roles se implementan con **Grupos de Django** (`Group`) y permisos propios, más clases de permiso en DRF.

| Rol | Descripción | Responsabilidades principales |
|---|---|---|
| **Administrador** | Control total del sistema | Gestionar usuarios y roles, configurar tarifas y parámetros (días de gracia, límites), dar de baja activos, desbloquear contratistas, ver todos los reportes y acceder a Django Admin. |
| **Bodeguero** | Custodia física del inventario | Registrar y editar activos, ingresarlos a una bodega, hacer traslados entre bodegas o obras, enviar a mantenimiento y registrar mantenimientos realizados. |
| **Encargado de entrega/recepción** (inspector) | Revisa los equipos al salir y al volver | Crear entregas (checklist de salida y firma del responsable), registrar devoluciones (estado, horómetro, daños, firma) y reportar daños o faltantes. |
| **Ventas** | Relación comercial con contratistas, arriendos y cobros | Registrar contratistas y obras, crear las solicitudes de arriendo (contratista, obra, activos o paquetes y fechas), armar los paquetes de maquinaria, revisar la disponibilidad del catálogo, revisar y emitir los cobros, registrar los pagos, hacer seguimiento de la morosidad y solicitar al Administrador el desbloqueo de un contratista. |

> **Separación de funciones:** Ventas **crea** el préstamo, pero **no lo entrega ni lo recibe** físicamente; eso lo hace el Encargado E/R. Así nadie controla el proceso completo por sí solo, lo que reduce las pérdidas y los cobros inexactos.

### Matriz de permisos

| Acción | Admin | Bodeguero | Encargado E/R | Ventas |
|---|:-:|:-:|:-:|:-:|
| Gestionar usuarios y roles | ✅ | ❌ | ❌ | ❌ |
| Crear/editar activos | ✅ | ✅ | 👁️ | 👁️ |
| Gestionar paquetes de maquinaria | ✅ | 👁️ | 👁️ | ✅ |
| Dar de baja un activo | ✅ | ⚠️ solicita | ❌ | ❌ |
| Traslados entre bodegas | ✅ | ✅ | ❌ | ❌ |
| Crear solicitud de arriendo (préstamo) | ✅ | ❌ | 👁️ | ✅ |
| Registrar entrega o devolución | ✅ | 👁️ | ✅ | 👁️ |
| Programar y registrar mantenimiento | ✅ | ✅ | ⚠️ reporta falla | ❌ |
| Gestionar contratistas y obras | ✅ | 👁️ | 👁️ | ✅ |
| Desbloquear un contratista moroso | ✅ | ❌ | ❌ | ⚠️ solicita |
| Ver cobros y reportes | ✅ | ❌ | ❌ | ✅ |
| Registrar pago de un cobro | ✅ | ❌ | ❌ | ✅ |
| Configurar tarifas | ✅ | ❌ | ❌ | 👁️ |
| Acceder a Django Admin | ✅ | ❌ | ❌ | ❌ |

✅ total · 👁️ solo lectura · ⚠️ parcial o solicitud · ❌ sin acceso

---

## 3. Flujos principales

### 3.1 Ciclo de vida de un activo (máquina de estados)

```
              ┌────────────── entrega ──────────────┐
              │                                     ▼
 [Alta] ─► DISPONIBLE ◄──── devolución OK ──── EN_USO
              │   ▲                                 │
   envío a    │   │ mantenimiento                   │ devolución con daño
   mantención ▼   │ finalizado                      │ o mantención vencida
           MANTENIMIENTO ◄──────────────────────────┘
              │
              │ irreparable / pérdida (solo Admin)
              ▼
         DADO_DE_BAJA  (estado final, no se puede volver a prestar)
```

Reglas:
- Solo se entrega un activo en estado **DISPONIBLE**.
- Si el mantenimiento preventivo de un activo está vencido, no se puede entregar.
- Cada cambio de estado genera un registro en `HistorialEstado` (quién, cuándo, de qué estado a cuál y motivo). Ese registro forma la **hoja de vida** del equipo.
- Los cambios de estado se hacen solo desde la capa de servicios (`services.py`), nunca editando el campo directamente.

### 3.2 Entrega (préstamo)

1. Ventas (o el Admin) registra la **solicitud de arriendo** para un contratista, una obra y unas fechas, con **activos individuales y/o paquetes**. El sistema muestra una cotización en CLP (ver 3.7).
2. El sistema revisa que el contratista **no esté bloqueado** y que haya suficientes activos disponibles en cada categoría pedida.
3. Si hay paquetes, el encargado de E/R **asigna activos concretos** a cada ítem (por ejemplo, el paquete pide 2 rotomartillos y se escanean `RTM-0004` y `RTM-0011`). El sistema valida que la cantidad por categoría coincida.
4. El encargado de E/R revisa el estado de cada activo (checklist), anota el horómetro de salida y toma fotos opcionales.
5. El **responsable de obra firma** en un canvas (pantalla táctil o mouse).
6. Los activos pasan a **EN_USO** y se genera el comprobante de entrega (vista imprimible o PDF).

### 3.3 Devolución

1. El encargado de E/R busca el préstamo activo.
2. Registra por cada activo el estado de recepción, el horómetro de llegada, los daños y los faltantes.
3. El responsable de obra firma la recepción.
4. El sistema:
   - suma las horas de uso (`horometro_llegada - horometro_salida`) al activo, si tiene horómetro;
   - suma **1 uso** al activo (`usos_totales` y `usos_desde_mantencion`);
   - calcula el **cobro en CLP** por día y mes, más los recargos por atraso y daños (ver 3.7);
   - pasa el activo a **DISPONIBLE**, o **automáticamente a MANTENIMIENTO** si tiene daño o si alcanzó su umbral de usos, horas o días (ver 3.5).

### 3.4 Morosidad y bloqueo automático

- Una tarea programada (`python manage.py revisar_morosidad`, ejecutada por **cron** en la EC2) corre todos los días:
  - Si un préstamo pasó su `fecha_devolucion_pactada` y no se ha devuelto, queda **atrasado** y se genera una **alerta**.
  - Si el atraso supera los `DIAS_GRACIA` (configurable), el contratista queda **BLOQUEADO** y no se le pueden hacer entregas nuevas.
- Solo el Administrador puede desbloquearlo, y debe indicar un motivo, que queda registrado.
- Las alertas se muestran en el dashboard. Enviar correo es opcional.

### 3.5 Mantenimiento preventivo

- Cada **categoría** tiene un plan por defecto, que el Admin puede ajustar por activo. El plan combina tres criterios y gana **el que ocurra primero**:
  - **Usos**: un uso es un arriendo completado, es decir, un préstamo devuelto.
  - **Horas de horómetro**: solo para maquinaria con motor.
  - **Días** desde la última mantención.

#### Umbrales por defecto

| Grupo de categorías | Ejemplos | Cada N usos | Cada N horas | Cada N días |
|---|---|:-:|:-:|:-:|
| Herramientas eléctricas menores | Taladro, esmeril angular, lijadora, sierra circular | **15** | — | 180 |
| Herramientas eléctricas pesadas | Rotomartillo, demoledor, cortadora de pavimento | **10** | — | 120 |
| Maquinaria ligera a motor | Generador, compactadora (placa o canguro), betonera, vibrador de inmersión, motobomba | **8** | 200 | 90 |
| Equipos de altura y acceso | Andamio, escalera telescópica, alzaprimas | **20** | — | 180 (inspección) |

Reglas:
- **Al registrar una devolución**, si `usos_desde_mantencion >= cada_usos`, el activo pasa **automáticamente** a `MANTENIMIENTO` (no vuelve a DISPONIBLE) y se genera una alerta para el bodeguero.
- Si se alcanza el umbral de horas o de días, el comando diario `revisar_mantenimientos` marca el activo como vencido. Si está en bodega, lo pasa a `MANTENIMIENTO`. Si está EN_USO, genera una alerta para que se recupere al devolverlo.
- **Alerta "próxima"**: cuando faltan **2 usos o menos**, el 10 % de las horas o 7 días.
- Un activo en `MANTENIMIENTO` o con la mantención vencida **no se puede entregar**.
- El bodeguero registra la mantención (tipo, fecha, técnico, costo en CLP y observaciones). Con eso se reinician los contadores (`usos_desde_mantencion = 0`, horas y fecha) y el activo vuelve a `DISPONIBLE`.

### 3.6 Paquetes de maquinaria

Un **paquete** es un conjunto predefinido de equipos que se arrienda junto a una constructora o subcontratista, con una tarifa propia del paquete (normalmente con descuento frente a la suma de las tarifas individuales).

- El paquete se define por **categorías y cantidades**, no por activos específicos. Por ejemplo, "2 rotomartillos" y no "RM-004". Así el paquete sigue sirviendo aunque un equipo concreto esté en mantención.
- Al entregar, el encargado de E/R asigna los activos concretos que estén disponibles (ver 3.2).
- Un préstamo puede combinar **paquetes y activos sueltos**.
- Si falta un equipo del paquete en la devolución, se registra como faltante en ese activo y se cobra el daño o la pérdida. El resto del paquete se devuelve con normalidad.
- Solo se pueden arrendar los paquetes marcados como activos. Ventas o el Admin los crean y editan.

Paquetes de ejemplo para los datos semilla:

| Paquete | Contenido | Tarifa diaria | Tarifa mensual |
|---|---|--:|--:|
| Kit Obra Gruesa | 1 betonera, 1 vibrador de inmersión, 2 rotomartillos, 1 generador | $85.000 | $1.600.000 |
| Kit Demolición | 1 demoledor, 1 rotomartillo, 1 esmeril angular, 1 generador | $70.000 | $1.300.000 |
| Kit Terminaciones | 2 taladros, 1 lijadora, 1 sierra circular, 1 esmeril angular | $35.000 | $650.000 |
| Kit Compactación | 1 placa compactadora, 1 canguro, 1 motobomba | $60.000 | $1.100.000 |

*(Valores referenciales en CLP para la demo.)*

### 3.7 Reglas de cobro (CLP)

- **Moneda:** peso chileno (CLP), **sin decimales**. Los montos se guardan como enteros (`PositiveIntegerField` / `PositiveBigIntegerField`) y se muestran con separador de miles: `$1.250.000`.
- **Configuración regional:** `LANGUAGE_CODE = "es-cl"`, `TIME_ZONE = "America/Santiago"` y `USE_THOUSAND_SEPARATOR = True`.
- **Tarifas:** cada categoría y cada paquete tienen una `tarifa_diaria` y una `tarifa_mensual`. Como referencia, la tarifa mensual equivale a unos 20 días de la diaria.
- **Precios congelados:** al crear el préstamo se copian las tarifas vigentes en la línea (`tarifa_diaria_aplicada` y `tarifa_mensual_aplicada`). Si después cambian las tarifas, los arriendos que ya existen no se ven afectados.

**Cálculo por línea** (cada activo suelto o cada paquete):

```
dias = (fecha_devolucion_real - fecha_entrega).days, mínimo 1   (cualquier fracción de día cuenta como día)

si dias < 30:
    arriendo = dias × tarifa_diaria
si no:
    meses = dias // 30
    resto = dias % 30
    arriendo = meses × tarifa_mensual + min(resto × tarifa_diaria, tarifa_mensual)
```

El `min(...)` sirve para que los días sobrantes nunca cuesten más que un mes completo.

**Recargos y total:**

```
dias_atraso   = max(0, fecha_devolucion_real - fecha_devolucion_pactada)
recargo_atraso = dias_atraso × tarifa_diaria × RECARGO_ATRASO   (por defecto 0,5 = +50 %)
cargo_danos   = monto ingresado por el encargado E/R en la devolución
neto  = Σ arriendo + Σ recargo_atraso + Σ cargo_danos
iva   = round(neto × 0,19)
total = neto + iva
```

- `RECARGO_ATRASO`, `DIAS_GRACIA` y la tasa de IVA son **parámetros configurables** por el Admin.
- Ejemplo: un rotomartillo a $15.000 por día y $300.000 por mes, arrendado 45 días → 1 × $300.000 + min(15 × $15.000, $300.000) = **$525.000 neto**.

### 3.8 Identificación única de cada máquina (código + QR)

Cada activo físico tiene un **identificador único e inmutable**. Con él se rastrea su hoja de vida, sus préstamos y, sobre todo, sus **mantenciones**.

| Identificador | Ejemplo | Origen | Uso |
|---|---|---|---|
| **Código interno** | `RTM-0004` | Se autogenera: prefijo de la categoría + correlativo de 4 dígitos | Identificador principal en todo el sistema |
| **Número de serie** | `SN-HD38291-B` | Lo pone el fabricante y se ingresa a mano | Garantías y servicio técnico externo |
| **Código QR** | Etiqueta adhesiva en la máquina | Se genera con la URL del activo | Escanear para abrir la ficha o registrar una mantención |

**Código interno**
- Cada `CategoriaActivo` tiene un `prefijo_codigo` (por ejemplo, `RTM` rotomartillo, `GEN` generador, `CMP` compactadora, `TAL` taladro o `BET` betonera).
- Al crear el activo, `services.py` asigna el siguiente correlativo de esa categoría dentro de un `transaction.atomic()` con `select_for_update()`, para que dos usuarios no obtengan el mismo número al mismo tiempo.
- El código **no se edita ni se reutiliza**, aunque el activo se dé de baja. Así la trazabilidad histórica no se pierde.

**Código QR y etiqueta**
- El QR guarda la URL `http://<host>/activos/RTM-0004/`. Se genera **al vuelo** con la librería `qrcode` (no se guarda como imagen): así, si cambia la IP de la EC2, basta con reimprimir las etiquetas. `SITE_URL` en `.env` fija la URL impresa.
- La vista **"Imprimir etiquetas"** genera una hoja con varias etiquetas (QR, código, nombre y categoría) para imprimirlas y pegarlas en las máquinas.
- **Escaneo:**
  - Con la cámara nativa del celular: abre la ficha del activo (pide iniciar sesión si no hay sesión).
  - Dentro de la app, con `html5-qrcode`, en las pantallas de **entrega, devolución y mantención**: se escanea la máquina y queda seleccionada, sin necesidad de escribir el código.
  - ⚠️ El navegador solo permite usar la cámara en vivo con **HTTPS** (o en `localhost`). Si la EC2 queda con `http://<IP>`, se usa el modo **"tomar foto del QR"** (`<input type="file" capture>` + `Html5Qrcode.scanFile`), que funciona sin HTTPS. Además, siempre se puede **escribir el código a mano**.

**Mantenciones ligadas al identificador**
- Cada mantención queda asociada al activo y además recibe un **folio propio** (`MNT-2026-0001`).
- **Flujo del bodeguero:**
  1. Escanea el QR de la máquina.
  2. Se abre su ficha, con los usos, horas y días que le quedan antes de la mantención.
  3. Toca "Registrar mantención".
  4. Completa el formulario, que se guarda con el folio.
- La **hoja de vida** de cada código muestra la línea de tiempo completa: alta, préstamos, traslados, todas sus mantenciones (folio, fecha, técnico y costo) y los cambios de estado.

---

## 4. Modelo de datos

```
Usuario (AbstractUser) ── rol vía Group
Bodega ──< Activo >── CategoriaActivo
Obra ──< Bodega (opcional: bodega de obra)
Contratista ──< Obra
Contratista ──< Prestamo ──< DetallePrestamo >── Activo
Prestamo ──1 FirmaEntrega / FirmaDevolucion
Activo ──< HistorialEstado
Activo ──< Traslado (bodega_origen → bodega_destino)
Activo ──1 PlanMantenimiento ──< Mantenimiento
PaqueteMaquinaria ──< ItemPaquete >── CategoriaActivo
Prestamo ──< PrestamoPaquete >── PaqueteMaquinaria
PrestamoPaquete ──< DetallePrestamo   (activos asignados al paquete)
Alerta (genérica: morosidad, mantención, daño)
Cobro ──1 Prestamo
```

### Entidades y campos clave

**usuarios**
- `Usuario`: extiende `AbstractUser`. Agrega `rut`, `telefono` y `cargo`. El rol se asigna con `groups`.

**activos**
- `CategoriaActivo`: `nombre`, `prefijo_codigo` (único, por ejemplo `RTM`), `descripcion`, `tarifa_diaria` (CLP), `tarifa_mensual` (CLP), `requiere_horometro` y el plan de mantención por defecto (`mant_cada_usos`, `mant_cada_horas`, `mant_cada_dias`).
- `Bodega`: `nombre`, `tipo` (CENTRAL / OBRA), `direccion`, `obra` (FK opcional), `encargado` (FK Usuario).
- `Activo`: `codigo` (único, autogenerado e inmutable, ver 3.8), `qr` (imagen), `nombre`, `categoria`, `marca`, `modelo`, `numero_serie`, `fecha_adquisicion`, `valor_compra`, `estado` (choices), `bodega_actual`, `horas_uso_totales`, `usos_totales`, `usos_desde_mantencion`, `foto` y `activo` (soft delete).
- `HistorialEstado`: `activo`, `estado_anterior`, `estado_nuevo`, `usuario`, `fecha`, `motivo` y `referencia` (préstamo o mantención).
- `Traslado`: `activo`, `bodega_origen`, `bodega_destino`, `usuario`, `fecha` y `observacion`.
- `PaqueteMaquinaria`: `codigo`, `nombre`, `descripcion`, `tarifa_diaria` (CLP), `tarifa_mensual` (CLP), `activo` (si se puede arrendar) y `creado_por`.
- `ItemPaquete`: `paquete`, `categoria` y `cantidad` (único por paquete y categoría).

**contratistas**
- `Contratista`: `rut` (único), `razon_social`, `contacto`, `email`, `telefono`, `estado` (ACTIVO / BLOQUEADO), `fecha_bloqueo` y `motivo_bloqueo`.
- `Obra`: `nombre`, `direccion`, `contratista`, `responsable_nombre`, `responsable_rut`, `fecha_inicio`, `fecha_fin` y `activa`.

**prestamos**
- `Prestamo`: `codigo`, `contratista`, `obra`, `fecha_entrega`, `fecha_devolucion_pactada`, `fecha_devolucion_real`, `estado` (BORRADOR / ENTREGADO / ATRASADO / DEVUELTO / CERRADO), `creado_por`, `entregado_por` y `recibido_por`.
- `PrestamoPaquete`: `prestamo`, `paquete`, `tarifa_diaria_aplicada` y `tarifa_mensual_aplicada` (precios congelados).
- `DetallePrestamo`: `prestamo`, `activo`, `prestamo_paquete` (FK opcional: si el activo viene en un paquete), `tarifa_diaria_aplicada` y `tarifa_mensual_aplicada` (solo para activos sueltos), `horometro_salida`, `horometro_llegada`, `estado_salida`, `estado_llegada`, `observacion_dano` y `cargo_dano` (CLP).
- `Firma`: `prestamo`, `tipo` (ENTREGA / DEVOLUCION), `nombre_firmante`, `rut_firmante`, `imagen` (PNG desde canvas), `fecha`, `ip` y `hash` (SHA-256 de la imagen y los datos, para probar integridad).
- `Cobro`: `prestamo`, `dias_cobrados`, `dias_atraso`, `monto_arriendo`, `monto_atraso`, `monto_danos`, `neto`, `iva`, `total` (todos en CLP enteros), `estado` (PENDIENTE / PAGADO), `fecha_pago` y `registrado_por`.
- `ParametroSistema` (singleton): `dias_gracia`, `recargo_atraso` y `tasa_iva`. El Admin los edita.

**mantenimiento**
- `PlanMantenimiento`: `activo`, `cada_usos`, `cada_horas`, `cada_dias` (se copian de la categoría al crear el activo y se pueden editar), `ultima_fecha`, `ultimas_horas` y las propiedades calculadas `usos_restantes`, `horas_restantes`, `proxima_fecha`, `proxima` y `vencido`.
- `Mantenimiento`: `folio` (único, `MNT-AAAA-NNNN`), `activo`, `tipo` (PREVENTIVO / CORRECTIVO), `estado` (EN_CURSO / FINALIZADA), `fecha`, `horas_al_momento`, `tecnico`, `costo`, `descripcion` y `registrado_por`.

**alertas**
- `Alerta`: `tipo` (MOROSIDAD / MANTENCION_PROXIMA / MANTENCION_VENCIDA / DANO), `nivel` (INFO / WARNING / CRITICO), `mensaje`, `content_type` + `object_id` (GenericForeignKey), `leida`, `resuelta` y `fecha`.

---

## 5. Arquitectura

```
Navegador (Templates + JS fetch)
        │  HTTP :80
        ▼
     Nginx  ── sirve /static y /media
        │  proxy
        ▼
    Gunicorn ── Django + DRF
        │
        ▼
   PostgreSQL (localhost:5432)

   cron ─► manage.py revisar_morosidad / revisar_mantenimientos
```

Todo corre en **una sola instancia EC2** (Ubuntu 22.04/24.04).

### Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12+, Django 6.0, Django REST Framework |
| Base de datos | PostgreSQL 16 (`psycopg`) |
| Autenticación | Sesiones de Django (login con formulario). DRF usa `SessionAuthentication` y CSRF. |
| Frontend | Django Templates, Bootstrap 5, JS vanilla (fetch) y Chart.js para el dashboard |
| Firma digital | [signature_pad](https://github.com/szimmer/signature_pad) sobre `<canvas>`, enviada como base64 y guardada en un `ImageField` |
| Comprobantes | Vista HTML imprimible. Opcional: WeasyPrint o xhtml2pdf para PDF. |
| Configuración | `django-environ` o `python-decouple` con un archivo `.env` |
| Tareas programadas | Management commands de Django y `cron` (sin Celery, para simplificar) |
| Servidor | Gunicorn, Nginx y `systemd` |
| Extras útiles | `django-filter` (filtros en la API), `qrcode` + `Pillow` (generación de QR por activo) y `html5-qrcode` (escaneo con la cámara desde el navegador) |

---

## 6. Estructura del repositorio

```
BuildCorp/
├── README.md                  # Instrucciones de ejecución + IP pública EC2
├── prompts_ia.md              # Registro de consultas a IA
├── PLANIFICACION.md           # Este documento
├── requirements.txt
├── .env.example               # Variables de entorno de ejemplo (sin secretos)
├── .gitignore
├── manage.py
├── buildcorp/                 # Proyecto Django (settings, urls, wsgi)
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── usuarios/              # Usuario custom, login/logout, roles, permisos
│   ├── activos/               # Categorías, bodegas, activos, historial, traslados, paquetes
│   ├── contratistas/          # Contratistas, obras, bloqueo
│   ├── prestamos/             # Préstamos, detalle, firmas, cobros
│   ├── mantenimiento/         # Planes y registros de mantención
│   ├── alertas/               # Alertas + management commands
│   └── dashboard/             # Vista principal, KPIs, reportes
│
│   # Cada app sigue esta estructura:
│   #   models.py, admin.py, serializers.py, views.py (templates),
│   #   api.py (ViewSets DRF), urls.py, services.py (lógica de negocio),
│   #   permissions.py, tests/, templates/<app>/
│
├── templates/
│   ├── base.html              # Layout con navbar según rol
│   └── registration/login.html
├── static/
│   ├── css/
│   └── js/
│       ├── api.js             # Wrapper fetch con CSRF
│       ├── firma.js           # Integración signature_pad
│       └── dashboard.js
├── media/                     # Firmas y fotos (no versionado)
└── deploy/
    ├── nginx_buildcorp.conf
    ├── gunicorn.service
    ├── crontab.txt
    ├── setup_ec2.sh           # Script de instalación en EC2
    ├── actualizar.sh          # Despliegue automático (git pull + migrate + collectstatic + reinicio)
    ├── buildcorp-actualizar.service
    └── buildcorp-actualizar.timer  # Ejecuta actualizar.sh cada 2 minutos
```

---

## 7. API REST (DRF)

Base: `/api/v1/` · Autenticación por sesión · Permisos por rol con clases como `EsAdministrador`, `EsBodeguero`, `EsEncargadoER` y `EsVentas`.

| Recurso | Endpoints | Acciones extra |
|---|---|---|
| Activos | `GET/POST /activos/`, `GET/PUT/PATCH /activos/{id}/` | `POST /activos/{id}/cambiar-estado/`, `GET /activos/{id}/hoja-vida/`, `POST /activos/{id}/trasladar/`, `GET /activos/codigo/{codigo}/` (búsqueda por escaneo), `GET /activos/{id}/qr/` (PNG), `GET /activos/etiquetas/?ids=...` (hoja de etiquetas imprimible) |
| Categorías | `/categorias/` | — |
| Paquetes | `/paquetes/` (con sus ítems anidados) | `GET /paquetes/{id}/disponibilidad/` (revisa si hay stock para armarlo) |
| Bodegas | `/bodegas/` | `GET /bodegas/{id}/inventario/` |
| Contratistas | `/contratistas/` | `POST /contratistas/{id}/desbloquear/` (solo Admin) |
| Obras | `/obras/` | — |
| Préstamos | `/prestamos/` | `POST /prestamos/cotizar/` (calcula el monto en CLP sin guardar), `POST /prestamos/{id}/asignar-activos/`, `POST /prestamos/{id}/entregar/` (con firma), `POST /prestamos/{id}/devolver/` (con firma), `GET /prestamos/atrasados/` |
| Mantenimientos | `/mantenimientos/`, `/planes-mantenimiento/` | `GET /planes-mantenimiento/proximos/` |
| Alertas | `/alertas/` | `POST /alertas/{id}/marcar-leida/` |
| Dashboard | `GET /dashboard/resumen/` | KPIs: activos por estado, préstamos activos o atrasados, mantenciones vencidas y cobros pendientes |

Filtros con `django-filter`: estado, categoría, bodega, contratista y rango de fechas.

---

## 8. Pantallas (frontend)

| Pantalla | Roles | Descripción |
|---|---|---|
| Login | Todos | Formulario de sesión |
| Dashboard | Todos (contenido según rol) | KPIs, gráfico de activos por estado y alertas activas |
| Catálogo de activos | Todos | Tabla con filtros y badge de color por estado |
| Ficha / hoja de vida | Todos | Datos, historial de estados, préstamos, mantenciones y traslados |
| Escanear QR | Todos | Botón en la barra superior: se escanea una máquina y se abre su ficha |
| Imprimir etiquetas | Admin, Bodeguero | Elegir activos y generar una hoja de etiquetas QR |
| Bodegas e inventario | Admin, Bodeguero | Activos por bodega y formulario de traslado |
| Contratistas y obras | Admin, Ventas | CRUD con indicador de bloqueo |
| Paquetes de maquinaria | Admin, Ventas | CRUD de paquetes (categorías y cantidades), tarifas en CLP y disponibilidad |
| Nuevo préstamo | Admin, Ventas | Elegir contratista, obra, paquetes y/o activos sueltos y fechas, y ver la cotización en CLP |
| Entrega | Encargado E/R | Checklist, horómetro y **canvas de firma** |
| Devolución | Encargado E/R | Estado de llegada, daños, horómetro y **canvas de firma** |
| Comprobante | Todos | Vista imprimible con las firmas |
| Mantenimientos | Admin, Bodeguero | Calendario o lista de próximas y vencidas, y registro |
| Cobros | Admin, Ventas | Detalle calculado por préstamo |
| Alertas | Todos | Bandeja de alertas |

Diseño responsivo con Bootstrap. Las pantallas de entrega y devolución se piensan **para tablet o celular**, porque se usan en terreno.

---

## 9. Django Admin personalizado

- `list_display`, `list_filter`, `search_fields` y `date_hierarchy` en todos los modelos.
- Badges de color para el estado con `format_html`.
- Inlines: `DetallePrestamo` y `Firma` dentro de `Prestamo`, y `HistorialEstado` y `Mantenimiento` dentro de `Activo`.
- **Acciones masivas**: "Enviar a mantenimiento", "Dar de baja", "Desbloquear contratista" y "Exportar CSV".
- Campos de solo lectura para la auditoría (firmas, hash, historial).
- Vista previa de la imagen de la firma en el admin.
- Títulos propios: `admin.site.site_header = "BuildCorp – Administración"`.

---

## 10. Seguridad

- `DEBUG=False` en producción, `SECRET_KEY` y las credenciales de la base de datos en `.env` (fuera del repositorio).
- `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` con la IP o DNS de la EC2.
- `@login_required` y `PermissionRequiredMixin` en las vistas, y `permission_classes` en la API.
- Validaciones de negocio en `services.py`, usando `transaction.atomic()` para entregas y devoluciones.
- La firma queda guardada con un hash, la fecha y la IP, y no se puede editar después de creada.
- PostgreSQL escucha solo en `localhost`. El Security Group abre solo los puertos 22 (tu IP) y 80.

---

## 11. Despliegue en AWS EC2 (AWS Academy)

1. Lanzar una EC2 Ubuntu (t2.micro o t3.small) con un Security Group que abra **22** y **80**.
2. Instalar los paquetes: `python3-venv`, `postgresql`, `nginx` y `git`.
3. Crear la base de datos y el usuario en PostgreSQL.
4. Clonar el repositorio, crear el virtualenv, ejecutar `pip install -r requirements.txt` y configurar `.env`.
5. Ejecutar `migrate`, `collectstatic`, `createsuperuser` y el comando de datos semilla (`cargar_roles` y datos demo).
6. Configurar Gunicorn como servicio `systemd`.
7. Configurar Nginx como reverse proxy, junto con `/static` y `/media`.
8. Instalar el `crontab` para morosidad y mantenimientos.
9. Comprobar el acceso en `http://<IP_PUBLICA>/` y anotar la IP en el `README.md`.
10. Activar el despliegue automático: un timer de systemd revisa `origin/main` cada 2 minutos y ejecuta `deploy/actualizar.sh` si hay commits nuevos. Se eligió este enfoque (el servidor consulta GitHub) en vez de GitHub Actions por SSH porque no requiere guardar la llave `.pem` en GitHub, ni abrir el puerto 22 a internet, y sigue funcionando aunque cambie la IP.

> ⚠️ **AWS Academy:** la IP pública **cambia cada vez que se reinicia el laboratorio**. Si el lab lo permite, asigna una **Elastic IP**. Si no, actualiza `ALLOWED_HOSTS` y el README antes de la evaluación. Deja todo automatizado en `deploy/setup_ec2.sh`.

---

## 12. Plan de trabajo por fases

| Fase | Contenido | Entregable verificable |
|---|---|---|
| **0. Setup** | Repositorio en GitHub, virtualenv, proyecto Django, conexión a PostgreSQL local, settings por entorno y `.env` | `runserver` funcionando contra PostgreSQL |
| **1. Usuarios y roles** | Usuario custom, grupos y permisos, login/logout, `base.html` con menú según rol | Inicio de sesión con los 4 roles de prueba |
| **2. Activos (RF1)** | Modelos, admin, máquina de estados en `services.py`, historial, bodegas, traslados, **paquetes**, **código autogenerado + QR + etiquetas**, API y templates del catálogo | Crear un activo y un paquete, cambiar el estado del activo y ver su hoja de vida |
| **3. Contratistas y obras** | CRUD, estado de bloqueo, admin y API | Contratista creado con una obra |
| **4. Préstamos y firma (RF2)** | Préstamo, detalle, préstamos con paquetes y activos sueltos, asignación de activos, entrega y devolución con signature_pad, cálculo de cobro en CLP (día/mes, atraso, IVA) y comprobante | Ciclo completo: entrega firmada de un paquete → devolución firmada → cobro correcto |
| **5. Mantenimiento (RF3)** | Planes por usos, horas y días, paso automático a MANTENIMIENTO al devolver, bloqueo de entrega si está vencido y registro de mantención | Un activo que llega a su umbral de usos pasa solo a MANTENIMIENTO al devolverlo |
| **6. Alertas y morosidad (RF4)** | Modelo Alerta, comandos `revisar_morosidad` y `revisar_mantenimientos`, bloqueo automático y desbloqueo por el Admin | Un préstamo vencido bloquea al contratista |
| **7. Dashboard y reportes** | KPIs, gráficos y exportación a CSV | Dashboard con datos reales |
| **8. Admin y pulido** | Personalización del admin, responsive, validaciones, tests básicos y datos semilla | Revisión completa de todas las pantallas |
| **9. Despliegue** | EC2, Nginx, Gunicorn, PostgreSQL y cron | App pública en `http://<IP>/` |
| **10. Documentación** | `README.md`, `prompts_ia.md` y capturas | Repositorio listo para entregar |

> Durante todo el proyecto, registra en `prompts_ia.md` cada consulta relevante hecha a la IA (fecha, herramienta, prompt resumido y para qué se usó).

---

## 13. Datos semilla (para la demo)

Comando `python manage.py cargar_demo` que crea:
- 4 usuarios: `admin`, `bodeguero`, `encargado` y `ventas`.
- 2 bodegas (Central y Obra Norte), alrededor de 10 categorías con tarifas en CLP y umbrales de mantención, y unos 30 activos en distintos estados (algunos a 1 o 2 usos de su mantención).
- Los 4 paquetes de ejemplo de la sección 3.6.
- 3 contratistas: uno activo, uno con un préstamo atrasado y uno bloqueado.
- Préstamos históricos con firmas de ejemplo y mantenciones vencidas y próximas.

---

## 14. Checklist de entrega

- [ ] Código fuente completo de Django y DRF en GitHub (público o compartido con el docente)
- [ ] Conexión a PostgreSQL y migraciones aplicadas sin errores
- [ ] Django Admin personalizado
- [ ] Autenticación por sesión y permisos por rol
- [ ] RF1: catálogo con estados y trazabilidad
- [ ] RF2: entrega y devolución con firma digital
- [ ] RF3: mantenimiento preventivo por horas o fecha
- [ ] RF4: alertas de morosidad y bloqueo automático
- [ ] Frontend responsivo que consume la API
- [ ] App desplegada en EC2 y accesible por la IP pública
- [ ] `README.md` con las instrucciones y la IP pública vigente
- [ ] `prompts_ia.md` con el registro de uso de IA

---

## 15. Decisiones pendientes

1. ~~¿Se incluye el rol Ventas?~~ **Resuelto:** sí. Ventas gestiona contratistas, solicitudes de arriendo y cobros (ver sección 2).
2. ~~Unidad de cobro~~ **Resuelto:** en CLP, por día y por mes (ver 3.7).
3. ~~Días de gracia~~ **Resuelto:** 3 días (parámetro editable por el Admin).
4. ~~Comprobante~~ **Resuelto:** vista HTML imprimible (Ctrl + P → PDF desde el navegador), sin PDF en el servidor.
5. **Notificaciones por correo:** opcional. Por defecto las alertas se muestran solo en el sistema.

---

## 16. Diseño de la interfaz

- Mundo visual **«Talonario de arriendo»**: riel en tinta carbón, folios en rojo, estados como timbres y una **copia de color por rol** (amarilla Ventas, rosada Bodega, celeste Encargado E/R, blanca Admin). Detalle en [DESIGN.md](DESIGN.md); contexto de producto en [PRODUCT.md](PRODUCT.md).
- **Dashboard por rol** (`/api/v1/dashboard/resumen/`, cargado con fetch):
  - Administrador: atrasos, bloqueados, cobros pendientes, mantenciones vencidas, solicitudes de desbloqueo/baja, activos por estado.
  - Bodeguero: mantenciones vencidas y próximas con acción "Registrar", equipos en taller, activos por estado.
  - Encargado E/R: entregas por hacer y devoluciones esperadas con botones "Entregar"/"Recibir" (tablas apiladas en celular).
  - Ventas: préstamos que vencen esta semana, cobros por cobrar, bloqueados y facturación de los últimos 6 meses.
- Alertas con `rol_destino`: cada rol ve las suyas; el Admin ve todas. El bodeguero puede **solicitar** una baja y Ventas un desbloqueo; ambas llegan como alerta al Admin.

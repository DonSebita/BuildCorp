# Guía de estudio para la defensa · BuildCorp

Esta guía reúne lo que necesitas dominar para defender el proyecto: qué hace, cómo está construido, **qué pasa en cada caso raro** (con el mensaje exacto que muestra el sistema), cómo funciona la infraestructura (EC2, Nginx, Gunicorn, etc.) y las preguntas que probablemente te harán, con su respuesta.

Todos los casos de la sección 6 se probaron ejecutando el código real contra la base de datos, no se dedujeron solo leyéndolo.

---

## Índice

1. [El proyecto en 1 minuto](#1-el-proyecto-en-1-minuto)
2. [Conceptos base de Django que te pueden preguntar](#2-conceptos-base-de-django)
3. [Modelo de datos](#3-modelo-de-datos)
4. [Los flujos paso a paso](#4-los-flujos-paso-a-paso)
5. [Cálculo del cobro con ejemplos](#5-cálculo-del-cobro-con-ejemplos)
6. [¿Qué pasa si…? Todas las excepciones](#6-qué-pasa-si-todas-las-excepciones)
7. [Puntos débiles y cómo responder](#7-puntos-débiles-y-cómo-responder)
8. [AWS EC2 explicado](#8-aws-ec2-explicado)
9. [Nginx explicado](#9-nginx-explicado)
10. [Gunicorn, systemd, cron, PostgreSQL y HTTPS](#10-gunicorn-systemd-cron-postgresql-y-https)
11. [El viaje completo de una petición](#11-el-viaje-completo-de-una-petición)
12. [Seguridad](#12-seguridad)
13. [Preguntas probables con respuesta](#13-preguntas-probables-con-respuesta)
14. [Comandos para una demo en vivo](#14-comandos-para-una-demo-en-vivo)
15. [Glosario](#15-glosario)

---

## 1. El proyecto en 1 minuto

> **BuildCorp** es un sistema **interno** para una empresa que arrienda herramientas y maquinaria ligera a contratistas. Controla **dónde está cada equipo** (código único + QR + hoja de vida), registra **entregas y devoluciones con firma digital** del responsable de obra, **calcula el cobro en pesos chilenos** (por día, por mes, con recargo por atraso, daños e IVA), **manda a mantenimiento** los equipos automáticamente cuando cumplen su límite de usos, horas o días, y **bloquea a los contratistas morosos**. Tiene 4 roles (Administrador, Ventas, Bodeguero, Encargado de entrega/recepción). Está hecho en **Django + Django REST Framework + PostgreSQL** y desplegado en **una EC2 de AWS** con **Nginx, Gunicorn y HTTPS**.

Los 4 requerimientos funcionales y dónde están:

| RF | Qué pide | Dónde está |
|---|---|---|
| RF1 | Catálogo con estados y trazabilidad | `apps/activos` (estados, `HistorialEstado`, `Traslado`, código + QR) |
| RF2 | Entrega/devolución con firma | `apps/prestamos/services.py`: `entregar()`, `devolver()`, `guardar_firma()` |
| RF3 | Mantenimiento preventivo | `apps/mantenimiento` (`PlanMantenimiento`, `revisar_plan()`) |
| RF4 | Morosidad y bloqueo | `revisar_morosidad()` + cron diario, `contratistas/services.py` |

---

## 2. Conceptos base de Django

| Concepto | Explicación corta | En BuildCorp |
|---|---|---|
| **MVT** (Model-View-Template) | El patrón de Django. *Model* = datos, *View* = lógica que responde a una URL, *Template* = HTML | `models.py`, `views.py`, `templates/` |
| **ORM** | Trabajas con la base de datos usando clases Python en vez de SQL | `Activo.objects.filter(estado="DISPONIBLE")` |
| **Migraciones** | Archivos que traducen los cambios de los modelos a cambios en las tablas (`makemigrations` las crea, `migrate` las aplica) | `apps/*/migrations/` |
| **App** | Un módulo con una responsabilidad | 7 apps: usuarios, activos, contratistas, prestamos, mantenimiento, alertas, dashboard |
| **DRF** | Django REST Framework: para construir la API JSON | `api.py` (ViewSets) + `serializers.py` |
| **Serializer** | Convierte objetos Python ↔ JSON y valida la entrada | `PrestamoEntradaSerializer` valida fechas e IDs |
| **ViewSet + Router** | Una clase que agrupa list/create/retrieve… y el router genera las URLs | `router.register("prestamos", PrestamoViewSet)` |
| **`@action`** | Endpoint extra dentro de un ViewSet | `POST /prestamos/{id}/entregar/` |
| **Sesión** | Al iniciar sesión, Django guarda una cookie `sessionid`; con ella sabe quién eres en cada petición | Login con formulario; la API usa `SessionAuthentication` |
| **CSRF** | Protección contra que otra página envíe formularios en tu nombre. Cada POST lleva un token | `{% csrf_token %}` en formularios y la cabecera `X-CSRFToken` en `fetch` (`static/js/api.js`) |
| **Grupos** | Conjuntos de usuarios con permisos | Cada rol es un `Group` |
| **Django Admin** | Panel de administración automático | Personalizado con badges de color, inlines, acciones masivas y exportar CSV |
| **Management command** | Un comando propio de `manage.py` | `revisar_morosidad`, `revisar_mantenimientos`, `cargar_demo` |
| **`transaction.atomic`** | Todo o nada: si algo falla, se deshace todo | Entregas, devoluciones, creación de préstamos |
| **`select_for_update`** | Bloquea las filas leídas hasta que termine la transacción, para que otro usuario no las modifique a la vez | Correlativos (`RTM-0004`, `P-2026-0001`, `MNT-2026-0001`) y activos al entregar |

### La capa de servicios (`services.py`)

Es la decisión de arquitectura más importante. **Toda la lógica de negocio** (validar, cambiar estados, calcular cobros) está en `services.py`, no en las vistas. Las vistas HTML, la API y el admin llaman a las mismas funciones. Así:

- Una regla se escribe una sola vez (por ejemplo, "no se entrega un equipo en mantenimiento").
- No se puede saltar una regla entrando por la API en vez de por la pantalla.
- Los errores de negocio se lanzan como `ValidationError` y la función `como_drf()` los convierte en **HTTP 400** con un mensaje legible.

### Permisos por rol

- `apps/usuarios/roles.py`: define los 4 roles. `rol_de(usuario)` devuelve el rol (el superusuario cuenta como Administrador).
- **Pantallas:** `RolRequeridoMixin` con `roles = (VENTAS,)`. Si no tienes el rol → **403**.
- **API:** `PermisoPorRol` lee `roles_lectura`, `roles_escritura` y `roles_por_accion` de cada ViewSet.
- **El Administrador siempre pasa** (`tiene_rol` devuelve `True` si el rol es ADMIN).

---

## 3. Modelo de datos

```
Usuario (AbstractUser) ── rol vía Group
Bodega ──< Activo >── CategoriaActivo
Contratista ──< Obra
Contratista ──< Prestamo ──< DetallePrestamo >── Activo
Prestamo ──< PrestamoPaquete >── PaqueteMaquinaria ──< ItemPaquete >── CategoriaActivo
Prestamo ──< Firma (ENTREGA / DEVOLUCION)
Prestamo ──1 Cobro
Activo ──< HistorialEstado          (hoja de vida)
Activo ──< Traslado
Activo ──1 PlanMantenimiento
Activo ──< Mantenimiento
Alerta  (genérica: apunta a cualquier objeto con GenericForeignKey)
ParametroSistema (una sola fila: días de gracia, recargo, IVA)
```

Detalles que conviene saber:

- **`CategoriaActivo`** guarda las tarifas (diaria y mensual), si requiere horómetro, el plan de mantención por defecto y el `ultimo_correlativo` para generar códigos.
- **`Activo.estado`** es `editable=False`: no se puede cambiar desde formularios ni desde el admin, solo con `cambiar_estado()`.
- **`DetallePrestamo`** es la línea de un préstamo (un equipo). Si viene dentro de un paquete apunta a `prestamo_paquete`; si es suelto, guarda su propia tarifa.
- **`PrestamoPaquete`** guarda la tarifa del paquete **congelada** al crear el préstamo.
- **`Firma`** tiene `unique_together = (prestamo, tipo)`: solo puede existir una firma de entrega y una de devolución por préstamo.
- **`Cobro`** es `OneToOne` con `Prestamo`: un préstamo tiene un solo cobro.
- **`ParametroSistema`** es un *singleton*: su `save()` fuerza `pk = 1`, así que siempre hay una sola fila.
- **`Alerta`** usa `GenericForeignKey` (`content_type` + `object_id`) para apuntar a un activo, un préstamo o un contratista con el mismo modelo. Tiene `rol_destino`: cada rol ve las suyas y el Admin ve todas.
- **`on_delete=PROTECT`** en préstamos, activos y contratistas: no se puede borrar un activo que tenga préstamos (se protege la historia). Para "eliminar" un activo se **da de baja** (`activo=False`).

### Los estados

**Activo:** `DISPONIBLE`, `EN_USO`, `MANTENIMIENTO`, `DADO_DE_BAJA`.

Transiciones permitidas (`TRANSICIONES` en `apps/activos/services.py`):

| Desde | Puede pasar a |
|---|---|
| DISPONIBLE | EN_USO, MANTENIMIENTO, DADO_DE_BAJA |
| EN_USO | DISPONIBLE, MANTENIMIENTO |
| MANTENIMIENTO | DISPONIBLE, DADO_DE_BAJA |
| DADO_DE_BAJA | *(ninguno: estado final)* |

**Préstamo:** `BORRADOR` ("Por entregar") → `ENTREGADO` → `ATRASADO` (lo pone el cron) → `DEVUELTO` → `CERRADO` (al pagar).

**Contratista:** `ACTIVO` / `BLOQUEADO`.

**Cobro:** `PENDIENTE` / `PAGADO`.

---

## 4. Los flujos paso a paso

### 4.1 Crear un arriendo (Ventas)

1. Ventas elige contratista, obra, fechas y paquetes y/o equipos sueltos.
2. Mientras elige, el navegador llama a `POST /api/v1/prestamos/cotizar/` y muestra el monto **sin guardar nada**.
3. Al crear, `crear_prestamo()` valida (en este orden): contratista no bloqueado → la obra es de ese contratista → hay al menos un paquete o activo → la devolución no es anterior a la entrega → cada activo suelto es entregable → hay stock para cada paquete.
4. Se crea el préstamo en estado `BORRADOR` con folio `P-2026-NNNN` y las tarifas **copiadas** (congeladas).

![Nuevo arriendo](img/24-nuevo-arriendo.png)

### 4.2 Entrega (Encargado E/R)

1. Si el préstamo tiene paquetes, el encargado **asigna equipos concretos** (escaneando QR o escribiendo el código). El sistema verifica que sean de la categoría que el paquete pide.
2. Checklist por equipo: estado de salida (solo "Bueno" o "Desgaste normal") y horómetro si la categoría lo requiere.
3. El responsable de obra escribe nombre y RUT y **firma en el canvas**.
4. `entregar()` dentro de una transacción: vuelve a validar todo, pasa cada activo a `EN_USO`, guarda la firma y pone el préstamo en `ENTREGADO` con `fecha_entrega = hoy`.

![Entrega](img/41-entrega.png)

### 4.3 Devolución (Encargado E/R)

1. Por cada equipo: estado de llegada (bueno, desgaste, **dañado**, **faltante**), horómetro de llegada, descripción del daño y cargo en CLP.
2. Firma del responsable.
3. `devolver()`:
   - suma las horas (`llegada − salida`) y **1 uso** a cada activo;
   - si está **dañado o faltante** → `MANTENIMIENTO` + alerta de daño;
   - si está bien → `DISPONIBLE` y luego `revisar_plan()`: si alcanzó su umbral → `MANTENIMIENTO`;
   - préstamo → `DEVUELTO`, resuelve las alertas de morosidad y **genera el cobro**.

![Devolución](img/42-devolucion.png)

### 4.4 Cobro y pago (Ventas)

Ventas revisa el cobro y registra el pago → cobro `PAGADO` y préstamo `CERRADO`.

### 4.5 Morosidad (cron diario)

`revisar_morosidad()` busca préstamos `ENTREGADO`/`ATRASADO` cuya fecha pactada ya pasó:

- los marca `ATRASADO` y crea una alerta para Ventas (nivel *Atención*);
- si los días de atraso **superan** los días de gracia (3 por defecto) → alerta *Crítica* y **bloquea** al contratista.

Con gracia = 3: día 1, 2 y 3 de atraso → solo alerta. **Día 4 → bloqueo.**

### 4.6 Mantenimiento (Bodeguero)

- El plan tiene hasta tres criterios: cada N **usos**, cada N **horas** y cada N **días**. **Gana el primero que se cumpla.**
- **Próxima** (alerta temprana): quedan ≤ 2 usos, ≤ 10 % de las horas o ≤ 7 días.
- **Vencida**: algún criterio llegó a 0 o menos.
- El bodeguero registra la mantención (tipo, técnico, costo, descripción). Recibe un folio `MNT-2026-NNNN`. Si la marca como terminada: contadores a cero y el activo vuelve a `DISPONIBLE`.

Umbrales de la demo:

| Grupo | Ejemplos | Usos | Horas | Días |
|---|---|:-:|:-:|:-:|
| Eléctricas menores | Taladro, esmeril, lijadora, sierra | 15 | — | 180 |
| Eléctricas pesadas | Rotomartillo, demoledor | 10 | — | 120 |
| Maquinaria a motor | Generador, compactadora, betonera, motobomba | 8 | 200 | 90 |
| Altura | Andamio | 20 | — | 180 |

---

## 5. Cálculo del cobro con ejemplos

```
días      = (devolución real − entrega).days, mínimo 1
arriendo  = días × diaria                                   si días < 30
          = meses × mensual + min(resto × diaria, mensual)  si días ≥ 30
atraso    = días_atraso × diaria × 0,5                       (recargo 50 %)
neto      = Σ arriendo + Σ atraso + Σ daños
IVA       = round(neto × 0,19)
total     = neto + IVA
```

Para los ejemplos: **rotomartillo** a $15.000/día y $300.000/mes.

| Caso | Cálculo | Neto | IVA | Total |
|---|---|--:|--:|--:|
| 3 días, a tiempo | 3 × 15.000 | $45.000 | $8.550 | $53.550 |
| Devuelto el mismo día | 0 días → mínimo **1** → 1 × 15.000 | $15.000 | $2.850 | $17.850 |
| Pactado 3 días, devuelto al día 5 | arriendo 5 × 15.000 = 75.000 + atraso 2 × 15.000 × 0,5 = 15.000 | $90.000 | $17.100 | $107.100 |
| 45 días | 1 × 300.000 + min(15 × 15.000, 300.000) | $525.000 | | |
| 59 días | 1 × 300.000 + min(29 × 15.000 = 435.000, **300.000**) | $600.000 | | |

**Kit Compactación 45 días** (lo que se ve en la captura): 1 × $1.100.000 + min(15 × $60.000, $1.100.000) = **$2.000.000** neto, $2.380.000 con IVA.

Claves para explicar:

- El `min(...)` evita que los días sobrantes cuesten más que un mes completo.
- Si se devuelve **antes** de lo pactado, se cobran solo los días reales (se usa la fecha real de devolución).
- Si se devuelve **tarde**, se cobran todos los días reales **y además** el recargo del 50 % por cada día de atraso.
- Los montos son **enteros** (`PositiveIntegerField`): el peso chileno no tiene decimales y así se evitan errores de redondeo.
- Las tarifas se **congelan** al crear el préstamo. Si el admin sube la tarifa mañana, los arriendos ya creados no cambian.
- Los parámetros (gracia, recargo, IVA) los edita el Administrador en *Parámetros*.

---

## 6. ¿Qué pasa si…? Todas las excepciones

Cada fila indica qué hace el sistema y el **mensaje exacto**. Los errores de la API responden **HTTP 400**; los de permisos, **HTTP 403**.

### 6.1 Fechas

| ¿Qué pasa si…? | Resultado | Mensaje / dónde |
|---|---|---|
| …la **devolución pactada es anterior a la entrega**? | **Rechazado**, tanto al cotizar como al crear | «La devolución pactada no puede ser anterior a la entrega.» (`cotizar()` y `crear_prestamo()`) |
| …entrega y devolución son **el mismo día**? | Permitido. Se cobra **1 día** (mínimo) | `dias_entre()` usa `max(1, …)` |
| …la fecha de entrega está **en el pasado**? | **Se permite crear.** Pero al entregar, `fecha_entrega` se reemplaza por **la fecha real de hoy**, y el cobro se calcula desde ahí | Ver sección 7 |
| …se devuelve **antes** de lo pactado? | Se cobran solo los días reales, sin recargo | `desglose()` usa la fecha real |
| …se devuelve **después** de lo pactado? | Días reales + recargo 50 % por día de atraso | `dias_atraso = max(0, real − pactada)` |
| …el préstamo se atrasa **3 días o menos**? | Estado `ATRASADO` + alerta a Ventas, **sin bloqueo** | `revisar_morosidad()` |
| …se atrasa **más de 3 días**? | Contratista **BLOQUEADO** + alerta crítica | «… con N días de atraso (gracia: 3)» |
| …el préstamo atrasado se devuelve? | Se resuelven las alertas de morosidad, **pero el contratista sigue bloqueado** hasta que el Admin lo desbloquee | `devolver()` solo llama a `resolver_alertas(..., MOROSIDAD)` |

![Error de fechas](img/25-error-fecha-devolucion.png)

### 6.2 Contratistas y obras

| ¿Qué pasa si…? | Resultado | Mensaje |
|---|---|---|
| …se crea un arriendo a un contratista **bloqueado**? | Rechazado. En la pantalla ni siquiera aparece seleccionable | «X está bloqueado por morosidad. Solo el Administrador puede desbloquearlo.» |
| …se bloquea **después** de crear el arriendo pero **antes** de entregarlo? | La entrega se rechaza (se vuelve a validar al entregar) | Mismo mensaje |
| …se bloquea mientras tiene equipos **en terreno**? | Puede devolverlos igual (la devolución no exige estar activo) | — |
| …se elige una **obra de otro contratista** (por la API)? | Rechazado | «La obra no pertenece al contratista.» |
| …se intenta **desbloquear sin motivo** o con menos de 5 letras? | Rechazado | «Escribe el motivo del desbloqueo (mínimo 5 caracteres).» |
| …se desbloquea a uno que **no está bloqueado**? | Rechazado | «El contratista no está bloqueado.» |
| …**Ventas** quiere desbloquear? | No puede: envía una **solicitud** que llega como alerta al Admin | «Solicitud enviada al Administrador.» |
| …se registra un contratista con un **RUT repetido**? | Rechazado por la base de datos (`rut` es `unique`) | Error del formulario |

### 6.3 Activos y stock

| ¿Qué pasa si…? | Resultado | Mensaje |
|---|---|---|
| …se presta un activo **en mantenimiento**? | Rechazado | «DEM-0002 no está disponible (Mantenimiento).» |
| …se presta un activo **en uso**? | Rechazado | «AND-0001 no está disponible (En uso).» |
| …se presta un activo con la **mantención vencida** (aunque figure disponible)? | Rechazado; además no aparece en la lista | «X tiene la mantención vencida y no se puede entregar.» |
| …no hay **stock** para un paquete? | Rechazado; en pantalla aparece «SIN STOCK» y qué falta | «No hay stock para «Kit Demolición»: falta Demoledor.» |
| …no se elige **ningún** paquete ni activo? | Rechazado | «Agrega al menos un paquete o un activo.» |
| …el **mismo activo** se pone en **dos arriendos** sin entregar? | **Se permite crear ambos** (en borrador el equipo sigue disponible). Al entregar el segundo, se rechaza | «AND-0004 no está disponible (En uso).» |
| …se asigna a un paquete un equipo de una **categoría que no pide**? | Rechazado | «El paquete no pide más rotomartillo.» |
| …se asigna un equipo **que ya está en el préstamo**? | Rechazado | «RTM-0004 ya está en este préstamo.» |
| …se escanea un **código que no existe**? | Rechazado | «No existe el activo XYZ-0001.» |
| …se intenta **entregar** sin haber asignado todos los equipos del paquete? | Rechazado | «Faltan activos por asignar en «Kit…».» |
| …un activo dado de baja quiere volver a **disponible**? | Imposible: `DADO_DE_BAJA` es estado final | «no se puede pasar de Dado de baja a Disponible.» |
| …se da de baja un activo **en uso**? | Rechazado (primero debe volver) | «AND-0001: no se puede pasar de En uso a Dado de baja.» |
| …el **bodeguero** quiere dar de baja? | No puede: solo **solicita**, llega como alerta al Admin | «Solo el Administrador da de baja. El bodeguero puede solicitarlo.» |
| …se da de baja **sin motivo**? | Rechazado | «Indica el motivo de la baja.» |
| …se **traslada** un activo en terreno? | Rechazado | «X está en terreno; se traslada al devolverlo.» |
| …se traslada a la **misma bodega** donde ya está? | Rechazado | «X ya está en Bodega Central.» |
| …se intenta **borrar** un activo? | La API no tiene `DELETE` y las FK son `PROTECT`. Se da de baja | — |
| …se edita la **categoría** de un activo? | No se puede: el formulario de edición la oculta, porque la categoría define el código | — |
| …dos bodegueros crean un activo de la **misma categoría a la vez**? | Cada uno recibe un correlativo distinto (`select_for_update` sobre la categoría) | — |
| …se da de baja `RTM-0004`; ¿se **reutiliza** el código? | No. `ultimo_correlativo` solo sube | — |

### 6.4 Entrega y firma

| ¿Qué pasa si…? | Resultado | Mensaje |
|---|---|---|
| …se intenta **entregar dos veces** el mismo préstamo? | Rechazado | «P-2026-0001 ya fue entregado.» |
| …un equipo sale **dañado o faltante**? | Rechazado; la pantalla solo ofrece "Bueno" y "Desgaste normal" | «X no puede salir en estado dañado.» |
| …falta el **horómetro de salida** en maquinaria a motor? | Rechazado | «Anota el horómetro de salida de GEN-0001.» |
| …falta el **nombre o RUT** de quien firma? | Rechazado | «Falta el nombre o el RUT de quien firma.» |
| …no hay **firma**? | Rechazado | «Falta la firma.» |
| …la firma **no es una imagen válida**? | Rechazado | «La imagen de la firma no es válida.» / «La firma está vacía o no es un PNG.» |
| …se quiere **modificar una firma** ya guardada? | No se puede: no hay endpoint para editarla; en el admin es de solo lectura. Además `unique_together(prestamo, tipo)` impide una segunda | — |

### 6.5 Devolución

| ¿Qué pasa si…? | Resultado | Mensaje |
|---|---|---|
| …el **horómetro de llegada es menor** que el de salida? | Rechazado | «El horómetro de llegada de CAN-0001 es menor que el de salida.» |
| …falta el horómetro de llegada (equipo a motor)? | Rechazado (salvo que esté **faltante**) | «Anota el horómetro de llegada de X.» |
| …se marca **dañado o faltante sin descripción**? | Rechazado | «Describe el daño o faltante de X.» |
| …un equipo vuelve **dañado**? | Pasa a `MANTENIMIENTO` + alerta *Atención*; el cargo se suma al cobro | — |
| …un equipo **no vuelve** (faltante)? | Pasa a `MANTENIMIENTO` + alerta **Crítica**; se cobra el cargo ingresado. El resto del paquete se devuelve normal. Luego el Admin puede darlo de baja | — |
| …un equipo llega bien pero **cumplió su límite de usos**? | Pasa solo a `MANTENIMIENTO` (no vuelve a disponible) | `revisar_plan()` |
| …se devuelve un préstamo **ya devuelto** o que **no se ha entregado**? | Rechazado | «P-2026-0011 no está en terreno.» |

### 6.6 Cobros

| ¿Qué pasa si…? | Resultado | Mensaje |
|---|---|---|
| …se registra el **pago dos veces**? | Rechazado | «Este cobro ya está pagado.» |
| …se **cambia la tarifa** después de crear el préstamo? | El préstamo mantiene la tarifa vieja (congelada) | — |
| …se cambia el **IVA o el recargo**? | Afecta a los cobros que se calculen desde ahora | Aviso en la pantalla de parámetros |

### 6.7 Mantenimiento

| ¿Qué pasa si…? | Resultado | Mensaje |
|---|---|---|
| …se registra una mantención a un equipo **en terreno**? | Rechazado | «X está en terreno. Regístrala cuando vuelva.» |
| …a un equipo **dado de baja**? | Rechazado | «X está dado de baja.» |
| …la mantención **no termina** ("sigue en taller")? | Se guarda con estado *En curso*, el activo queda en `MANTENIMIENTO` | — |
| …un equipo vence por **días u horas** estando en bodega? | El cron diario lo pasa a `MANTENIMIENTO` y avisa al bodeguero | `revisar_mantenimientos()` |
| …vence estando **en terreno**? | No se puede cambiar su estado; alerta para mandarlo a taller al volver | — |

### 6.8 Permisos

| ¿Qué pasa si…? | Resultado |
|---|---|
| …alguien **sin sesión** entra a cualquier página? | Redirige al login |
| …alguien sin sesión llama a la **API**? | 403 |
| …el **Encargado** entra a Cobros? | **403 Forbidden** |
| …**Ventas** intenta entregar o devolver? | 403: solo el Encargado E/R (y el Admin) |
| …el **Bodeguero** intenta crear un arriendo? | 403 |
| …alguien que no es Admin entra a `/admin/`? | Django Admin pide un usuario `is_staff`; solo `admin` lo es |
| …se envía un POST **sin token CSRF**? | 403 de Django |

---

## 7. Puntos débiles y cómo responder

Es mejor que los conozcas tú antes de que te los encuentren. Para cada uno, una respuesta honesta y la mejora posible.

| Punto débil | Qué pasa | Cómo responder |
|---|---|---|
| **29 días cuestan más que 30** | Con el rotomartillo, 29 días = $435.000 y 30 días = $300.000 (tarifa mensual) | "La regla viene de la planificación: la tarifa mensual parte en el día 30. Para corregirlo, se aplicaría `min(días × diaria, mensual)` también bajo 30 días." |
| **Se puede crear un arriendo con fecha de entrega pasada** | No se valida que sea ≥ hoy. Al entregar, igual se usa la fecha real | "El cobro es correcto porque usa la fecha real de entrega. La mejora es validar `fecha_entrega >= hoy` al crear." |
| **Los arriendos en borrador no reservan equipos** | El mismo equipo puede estar en dos borradores; falla el segundo al entregar | "Es intencional: el equipo sigue disponible hasta salir físicamente. La entrega vuelve a validar dentro de una transacción con bloqueo de filas, así que nunca sale dos veces. Una mejora sería un estado RESERVADO." |
| **No se valida el dígito verificador del RUT** | Acepta cualquier texto de hasta 12 caracteres | "Se puede agregar un validador de módulo 11." |
| **El servidor acepta una firma en blanco** | Solo valida que sea un PNG; quien bloquea la firma vacía es el JavaScript | "El navegador lo impide en la pantalla. Una mejora es verificar en el servidor que la imagen tenga trazos." |
| **Cargo por daño negativo por la API** | El formulario lo impide (`min=0`), pero por API da error 500 (la base de datos lo rechaza) | "La base de datos protege el dato (`PositiveIntegerField` crea un CHECK en PostgreSQL), así que nunca se guarda. Falta convertirlo en un 400 con mensaje." |
| **Página 403 genérica** | Se ve el "403 Forbidden" plano de Django | "Falta una plantilla `403.html` propia." |
| **Atraso detectado una vez al día** | El estado `ATRASADO` aparece cuando corre el cron (03:00 hora Chile) | "Para un arriendo por días es suficiente; podría correr cada hora." |
| **Un bloqueado sigue bloqueado tras devolver** | Hay que desbloquearlo a mano | "Es intencional: la regla del caso dice que solo el Administrador desbloquea, y con motivo." |
| **Sin límite de intentos de login** | No hay protección contra fuerza bruta | "Se agregaría `django-axes` o un límite en Nginx (`limit_req`)." |
| **Una sola EC2** | Si la instancia cae, cae todo (sin alta disponibilidad) | "Lo pide el requerimiento RT6. En producción real se separaría la base en RDS y se usaría un balanceador." |

---

## 8. AWS EC2 explicado

### ¿Qué es EC2?

**EC2 (Elastic Compute Cloud)** es el servicio de AWS para arrendar **máquinas virtuales** (llamadas *instancias*). Es un computador en un datacenter de Amazon al que te conectas por internet. Pagas por hora mientras está encendida.

### Las piezas de una instancia

| Pieza | Qué es | En BuildCorp |
|---|---|---|
| **AMI** (Amazon Machine Image) | La "imagen" con el sistema operativo con que arranca | Ubuntu Server 26.04 LTS |
| **Tipo de instancia** | Cuánta CPU y RAM tiene | **t3.small**: 2 vCPU, 2 GB de RAM |
| **Familia "t"** | Instancias *burstable*: CPU base baja con créditos para picos; baratas y buenas para apps con poca carga | — |
| **EBS** (Elastic Block Store) | El disco virtual. **Persiste** aunque apagues la instancia | ~7 GB, 46 % usado |
| **Región y zona** | Dónde está físicamente | `us-east-1` (Virginia), zona `us-east-1c` |
| **IP privada** | Dirección dentro de la red de AWS (VPC) | `172.31.17.164` |
| **IP pública** | Dirección para entrar desde internet | `100.60.151.204` |
| **Security Group** | **Firewall virtual** que decide qué puertos entran | 22 (SSH), 80 (HTTP), 443 (HTTPS) |
| **Key pair** (`.pem`) | Llave para entrar por SSH. AWS guarda la pública; tú la privada | `buildcorp.pem` |
| **VPC** | Red privada virtual donde vive la instancia | La VPC por defecto |

### IP pública vs. Elastic IP

- La **IP pública normal cambia** cada vez que la instancia se **detiene y vuelve a arrancar** (y en AWS Academy, al reiniciar el laboratorio).
- Una **Elastic IP** es una IP fija que reservas y asocias a la instancia. AWS Academy a veces no la permite o limita.
- Por eso: los QR se generan al vuelo, y el README explica qué cambiar en `.env` si cambia la IP.

### AWS Academy (Learner Lab)

- Es un entorno de AWS con **crédito limitado** para estudiantes.
- La sesión del laboratorio dura unas horas; al terminar, **las instancias se detienen** (no se borran). Al volver a iniciar el lab, arrancan de nuevo con **otra IP pública**.
- El disco EBS se conserva: la base de datos y los archivos siguen ahí.

### SSH: cómo te conectas

```bash
ssh -i "buildcorp.pem" ubuntu@100.60.151.204
```

- `ssh` abre una terminal remota cifrada (puerto 22).
- `-i buildcorp.pem` es tu llave privada (por eso no se pide contraseña).
- `ubuntu` es el usuario por defecto de las AMI de Ubuntu.

### Por qué una sola instancia

El requerimiento RT6 pide Django y PostgreSQL **en la misma EC2**. Ventaja: simple y barato. Desventaja: no hay redundancia.

### ¿Qué hay corriendo en la EC2?

```
Puerto 22   sshd        ← tú (SSH)
Puerto 80   nginx       ← internet (HTTP)
Puerto 443  nginx       ← internet (HTTPS)
127.0.0.1:8000  gunicorn (1 maestro + 3 workers)   ← solo Nginx
127.0.0.1:5432  postgresql                          ← solo Django
```

**Gunicorn y PostgreSQL escuchan solo en `127.0.0.1` (localhost)**: desde internet no se puede llegar a ellos, aunque se abriera el puerto en el Security Group.

---

## 9. Nginx explicado

### ¿Qué es?

**Nginx** (se pronuncia "engine-x") es un **servidor web** y **proxy inverso**. Es la **puerta de entrada**: recibe todas las peticiones de internet y decide qué hacer con cada una.

### ¿Por qué no exponer Django directo?

- `runserver` es solo para desarrollo: lento, inseguro, un proceso.
- Gunicorn ejecuta Python bien, pero **no es bueno sirviendo archivos** ni manejando miles de conexiones lentas.
- Nginx es muy eficiente para eso. Cada uno hace lo que mejor sabe.

### Las 4 cosas que hace Nginx en BuildCorp

1. **Sirve los archivos estáticos** (`/static/` → CSS, JS, imágenes) directamente desde el disco, **sin pasar por Django**. Es mucho más rápido.
2. **Sirve los archivos subidos** (`/media/` → firmas y fotos).
3. **Proxy inverso**: todo lo demás lo reenvía a Gunicorn en `127.0.0.1:8000`.
4. **Termina el HTTPS**: descifra el tráfico TLS con el certificado de Let's Encrypt y habla con Gunicorn en HTTP plano dentro de la máquina.

### "Proxy inverso", en simple

Un **proxy** es un intermediario. Es **inverso** porque está del lado del **servidor** (no del cliente): el navegador cree que habla con Nginx, y Nginx le pasa la petición a Gunicorn por detrás y le devuelve la respuesta.

```
Navegador ──► Nginx ──► Gunicorn ──► Django
          ◄──       ◄──          ◄──
```

### La configuración real, línea por línea

Archivo `/etc/nginx/snippets/buildcorp_app.conf` (lo común):

```nginx
client_max_body_size 10M;      # tamaño máximo de una subida (fotos y firmas)

location /static/ {
    alias /home/ubuntu/BuildCorp/staticfiles/;   # carpeta que llena collectstatic
    expires 7d;                                  # el navegador lo guarda 7 días en caché
}
location /media/ {
    alias /home/ubuntu/BuildCorp/media/;         # firmas y fotos subidas
}
location / {                                     # todo lo demás → Django
    proxy_pass http://127.0.0.1:8000;            # Gunicorn
    proxy_set_header Host $host;                 # para que Django vea el dominio real (ALLOWED_HOSTS)
    proxy_set_header X-Real-IP $remote_addr;     # IP real del cliente
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # cadena de IPs (se guarda en la firma)
    proxy_set_header X-Forwarded-Proto $scheme;  # si vino por http o https
}
```

Archivo `/etc/nginx/sites-available/buildcorp` (los *server blocks*):

```nginx
# 1) Acceso por IP (HTTP). Es el "default_server": atiende cualquier nombre que no calce con otro bloque
server {
    listen 80 default_server;
    server_name _;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }   # validación de Let's Encrypt
    include snippets/buildcorp_app.conf;
}

# 2) El dominio por HTTP: solo redirige a HTTPS
server {
    listen 80;
    server_name 100-60-151-204.sslip.io;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }   # 301 = redirección permanente
}

# 3) HTTPS
server {
    listen 443 ssl;
    http2 on;
    server_name 100-60-151-204.sslip.io;
    ssl_certificate     /etc/letsencrypt/live/100-60-151-204.sslip.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/100-60-151-204.sslip.io/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;                         # solo versiones seguras de TLS
    add_header Strict-Transport-Security "max-age=31536000" always;   # HSTS: el navegador usará siempre HTTPS
    include snippets/buildcorp_app.conf;
}
```

Conceptos que salen aquí:

| Término | Significado |
|---|---|
| **server block** | Un "sitio" dentro de Nginx. Nginx elige cuál usar según el puerto (`listen`) y el nombre (`server_name`) que pidió el navegador |
| **location** | Regla según la ruta de la URL. Gana la más específica: `/static/` antes que `/` |
| **alias** | "Esta ruta corresponde a esta carpeta del disco" |
| **proxy_pass** | "Reenvía la petición a este servidor" |
| **default_server** | El bloque que atiende si ningún `server_name` coincide (por ejemplo, cuando entras por la IP) |
| **301** | Redirección permanente |
| **HSTS** | Le dice al navegador "durante un año, entra a este dominio solo por HTTPS" |
| **sites-available / sites-enabled** | Convención de Ubuntu: en *available* están las configuraciones; en *enabled* hay un enlace a las que están activas |
| **snippets** | Trozos reutilizables con `include` (así HTTP y HTTPS comparten la misma configuración de la app) |

### Por qué existe `collectstatic`

Cada app tiene sus archivos estáticos en su propia carpeta. `python manage.py collectstatic` los **copia todos a una sola carpeta** (`staticfiles/`) para que Nginx los sirva desde ahí. Con `DEBUG=False`, **Django no sirve los estáticos**: si Nginx no lo hiciera, la página se vería sin estilos.

### Comandos de Nginx

```bash
sudo nginx -t                    # revisa que la configuración no tenga errores
sudo systemctl reload nginx      # aplica cambios sin cortar conexiones
sudo tail -f /var/log/nginx/error.log
```

---

## 10. Gunicorn, systemd, cron, PostgreSQL y HTTPS

### Gunicorn

- Django es una aplicación **WSGI** (*Web Server Gateway Interface*): el estándar de Python para que un servidor web le pase peticiones a una app.
- **Gunicorn** es el servidor WSGI. Ejecuta `buildcorp.wsgi:application`.
- Usa un proceso **maestro** y **3 workers** (procesos que atienden peticiones en paralelo). Regla típica: `2 × CPU + 1`; con 2 vCPU y 2 GB de RAM, 3 es un número prudente.
- Escucha en `127.0.0.1:8000`, solo para Nginx. `--timeout 60` mata un worker que tarde más de 60 s.

### systemd

Es el administrador de servicios de Linux. Se encarga de **arrancar los programas al encender la máquina**, **reiniciarlos si se caen** y guardar sus logs.

`deploy/gunicorn.service` → instalado como `/etc/systemd/system/buildcorp.service`:

```ini
[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/BuildCorp
Environment=DJANGO_SETTINGS_MODULE=buildcorp.settings.prod    # usa la configuración de producción
ExecStart=/home/ubuntu/BuildCorp/.venv/bin/gunicorn buildcorp.wsgi:application --workers 3 --bind 127.0.0.1:8000 --timeout 60
Restart=on-failure                                            # si se cae, lo vuelve a levantar
[Install]
WantedBy=multi-user.target                                    # arranca solo al encender la EC2
```

Servicios activos en la EC2: `nginx`, `postgresql`, `buildcorp` (Gunicorn), `buildcorp-actualizar.timer` (despliegue automático) y `certbot.timer` (renovación del certificado).

### cron

Programador de tareas de Linux. El `crontab` del usuario `ubuntu`:

```
0 6 * * *  … manage.py revisar_morosidad        # todos los días a las 06:00
10 6 * * * … manage.py revisar_mantenimientos   # todos los días a las 06:10
```

Formato: `minuto hora día-del-mes mes día-de-la-semana`. La EC2 está en **UTC**, así que las 06:00 UTC son las **03:00 en Chile** (horario de verano, UTC−3). Se usó cron y no Celery porque son solo dos tareas diarias: más simple, sin Redis ni procesos extra.

### Despliegue automático

Un **timer de systemd** (`buildcorp-actualizar.timer`) ejecuta `deploy/actualizar.sh` cada 2 minutos:

1. `git fetch`; si no hay commits nuevos en `main`, termina.
2. Si hay: `git merge --ff-only`, `pip install` (solo si cambió `requirements.txt`), `migrate`, `collectstatic` y reinicio de Gunicorn.
3. Registra todo en `/home/ubuntu/buildcorp-deploy.log`. Un *lock* (`flock`) evita dos despliegues a la vez.

**¿Por qué no GitHub Actions?** Porque habría que guardar la llave `.pem` en GitHub, abrir el puerto 22 a todo internet y actualizar la IP cada vez que cambia. Así el servidor **consulta** a GitHub (modelo *pull*), y no al revés.

### PostgreSQL

- Base de datos relacional, versión 18, en la misma EC2.
- Escucha **solo en localhost**: no está expuesta a internet.
- Django se conecta con `DATABASE_URL=postgres://buildcorp:CLAVE@localhost:5432/buildcorp` (en el `.env`, que **no está en GitHub**).
- ¿Por qué PostgreSQL y no SQLite? Lo pide el requerimiento, soporta muchos usuarios a la vez, tiene `SELECT … FOR UPDATE` real (bloqueo de filas) y restricciones `CHECK`.

### HTTPS con Let's Encrypt y sslip.io

- **HTTPS** cifra el tráfico (contraseñas y firmas no viajan en texto plano). Además, **el navegador solo deja usar la cámara en vivo con HTTPS** (para escanear QR).
- **Let's Encrypt** entrega certificados **gratis**, pero **no los emite para una IP**: necesita un **nombre de dominio**.
- **sslip.io** es un DNS gratuito: `100-60-151-204.sslip.io` responde con la IP `100.60.151.204`. Así se tiene un dominio sin comprarlo.
- **certbot** pidió el certificado con el método *webroot*: Let's Encrypt visitó `http://…/.well-known/acme-challenge/…` para comprobar que controlamos el servidor (por eso esa `location` en Nginx).
- El certificado dura **90 días**; `certbot.timer` lo renueva solo.
- El acceso por `http://IP` se mantiene porque lo pide la evaluación.

### Configuración por entorno (`.env`)

| Variable | Para qué |
|---|---|
| `DEBUG=False` | En producción no se muestran errores con el código |
| `SECRET_KEY` | Firma las cookies de sesión y los tokens CSRF. Si se filtra, se podrían falsificar sesiones |
| `DATABASE_URL` | Conexión a PostgreSQL |
| `ALLOWED_HOSTS` | Nombres/IPs por los que Django acepta peticiones (protege contra ataques de *Host header*) |
| `CSRF_TRUSTED_ORIGINS` | Orígenes desde los que se aceptan formularios (necesario con HTTPS) |
| `SITE_URL` | La URL que se imprime dentro de los QR |
| `MOSTRAR_CREDENCIALES_DEMO` | Muestra u oculta el botón **?** del login |

`buildcorp/settings/` tiene `base.py` (común), `dev.py` (`DEBUG=True`) y `prod.py` (`DEBUG=False`, `X_FRAME_OPTIONS=DENY`, logs).

---

## 11. El viaje completo de una petición

Ejemplo: el encargado confirma una devolución desde la tablet.

1. El JavaScript hace `fetch("POST /api/v1/prestamos/12/devolver/")` con el JSON (estados, horómetros, firma en base64), la cookie de sesión y la cabecera `X-CSRFToken`.
2. **DNS**: `100-60-151-204.sslip.io` → `100.60.151.204`.
3. **Security Group** de AWS: el puerto 443 está abierto → pasa.
4. **Nginx** (puerto 443) descifra el TLS, ve que la ruta no es `/static/` ni `/media/` y la reenvía a `127.0.0.1:8000`, agregando `X-Forwarded-For` con la IP del cliente.
5. **Gunicorn** le entrega la petición a un worker libre, que llama a Django por WSGI.
6. **Django**: los middlewares cargan la sesión (quién eres) y validan el CSRF → el router de DRF encuentra `PrestamoViewSet.devolver` → `PermisoPorRol` revisa que seas Encargado o Admin.
7. **Servicio** `devolver()` dentro de `transaction.atomic()`: bloquea el préstamo (`select_for_update`), valida, actualiza activos, guarda la firma (archivo en `media/` + hash), genera el cobro. Si algo falla, **se deshace todo**.
8. **PostgreSQL** confirma la transacción.
9. Django responde JSON → Gunicorn → Nginx (cifra) → navegador, que muestra el resultado.

---

## 12. Seguridad

| Medida | Dónde |
|---|---|
| Contraseñas con hash (PBKDF2, el estándar de Django) | `Usuario` hereda de `AbstractUser` |
| Login por sesión; todas las vistas exigen sesión | `RolRequeridoMixin`, `IsAuthenticated` |
| Permisos por rol en pantallas **y** API | `permissions.py` |
| CSRF en formularios y `fetch` | `{% csrf_token %}` y `X-CSRFToken` |
| `DEBUG=False` en producción | `settings/prod.py` |
| Secretos en `.env`, fuera del repositorio | `.gitignore` |
| PostgreSQL y Gunicorn solo en localhost | `ss -tlnp` lo demuestra |
| HTTPS con TLS 1.2/1.3 y HSTS | Nginx |
| `X_FRAME_OPTIONS = DENY` (evita *clickjacking*) | `prod.py` |
| Firma con hash SHA-256, IP y fecha, no editable | `guardar_firma()` |
| Transacciones atómicas y bloqueo de filas | `services.py` |
| Estados que no se pueden editar a mano (`editable=False`) | modelos |
| Auditoría: historial de estados, quién entregó/recibió, quién desbloqueó y por qué | modelos |
| ORM con consultas parametrizadas (evita inyección SQL) | Django |
| Escape automático en templates y `esc()` en JS (evita XSS) | Django / `api.js` |

### ¿Qué prueba el hash de la firma?

`SHA-256(imagen + folio + tipo + nombre + RUT + fecha)`. Si alguien cambiara la imagen o los datos en la base de datos, el hash ya no coincidiría. Prueba **integridad** (que no se alteró). No es una firma electrónica avanzada con certificado de la Ley 19.799; es una firma simple con evidencia.

---

## 13. Preguntas probables con respuesta

**¿Por qué Django y no otro framework?**
Trae ORM, migraciones, autenticación, sesiones, CSRF y un panel de administración listos. DRF agrega la API con serializers y permisos. Para un sistema interno con muchos formularios y reglas, ahorra mucho trabajo.

**¿Por qué una API REST si ya hay templates?**
Las pantallas interactivas (cotización en vivo, entrega, devolución, dashboard) consumen la API con `fetch`, sin recargar la página. Además, la API permitiría en el futuro una app móvil u otra integración. Lo pide el RT5.

**¿Dónde está la lógica de negocio y por qué?**
En `services.py` de cada app. Las vistas, la API y el admin usan las mismas funciones, así que una regla no se puede saltar.

**¿Cómo evitas que dos encargados entreguen el mismo equipo al mismo tiempo?**
`entregar()` corre dentro de `transaction.atomic()` y bloquea las filas con `select_for_update()`. El segundo espera; cuando le toca, el equipo ya está `EN_USO` y `validar_entregable()` lo rechaza.

**¿Cómo se genera el código `RTM-0004`?**
Cada categoría guarda su `ultimo_correlativo`. Al crear un activo se bloquea la categoría (`select_for_update`), se suma 1 y se arma `prefijo-NNNN`. El código no se edita ni se reutiliza.

**¿Qué pasa si cambia la IP de la EC2?**
Se actualizan `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `SITE_URL` en el `.env` y se reinicia Gunicorn. Los QR se generan al vuelo, así que basta con reimprimir las etiquetas. Para HTTPS habría que sacar un certificado nuevo para el nuevo nombre sslip.io.

**¿Qué pasa si se reinicia la EC2?**
systemd vuelve a levantar Nginx, PostgreSQL, Gunicorn y los timers. Los datos están en el disco EBS, que se conserva.

**¿Cómo se despliega una actualización?**
`git push` a `main`. En menos de 2 minutos el timer de la EC2 lo detecta y ejecuta `actualizar.sh`.

**¿Qué hace `migrate`?**
Aplica en PostgreSQL los cambios de los modelos (crear tablas, columnas, índices) descritos en los archivos de migración.

**¿Qué es `DEBUG=False` y por qué importa?**
Con `DEBUG=True`, un error muestra el código, las variables y la configuración: un regalo para un atacante. Además, con `False` Django no sirve estáticos (lo hace Nginx).

**¿Por qué los montos son enteros?**
El CLP no tiene decimales. Con `float` aparecerían errores de redondeo (`0.1 + 0.2 ≠ 0.3`).

**¿Cómo funciona el bloqueo automático?**
Un cron diario ejecuta `revisar_morosidad`. Los préstamos vencidos pasan a `ATRASADO` con alerta; si el atraso supera los días de gracia, el contratista queda `BLOQUEADO`. Solo el Admin lo desbloquea y debe escribir el motivo, que queda guardado junto con quién y cuándo.

**¿Por qué Ventas no puede entregar?**
Separación de funciones: quien vende no controla la salida física. Reduce pérdidas y fraudes.

**¿Cómo funciona el escáner QR?**
El QR contiene la URL de la ficha (`https://…/activos/RTM-0004/`). Con la cámara del celular abre la ficha. Dentro de la app se usa `html5-qrcode`: con HTTPS, cámara en vivo; con HTTP, "tomar foto del QR". Siempre se puede escribir el código.

**¿Qué pruebas tiene?**
8 tests (`python manage.py test apps`): cálculo en CLP (menos de 30 días, 45 días, tope del resto, mínimo 1 día), código correlativo, ciclo completo por API (crear → entregar con firma → devolver → cobro), paso automático a mantenimiento por usos y bloqueo por morosidad.

**¿Qué personalizaste del Django Admin?**
Títulos propios, badges de color por estado, inlines (detalles y firmas dentro del préstamo; historial, plan y mantenciones dentro del activo), acciones masivas (enviar a mantenimiento, dar de baja, desbloquear, exportar CSV), vista previa de la firma y campos de auditoría en solo lectura.

**¿Qué es un GenericForeignKey y por qué lo usaste en Alerta?**
Una FK que puede apuntar a cualquier modelo (guarda el tipo y el id). Así una sola tabla de alertas sirve para activos, préstamos y contratistas.

**¿Cómo usaste la IA?**
Está registrado en `prompts_ia.md`, entrada por entrada: qué se pidió, qué hizo la IA y qué archivos cambió.

---

## 14. Comandos para una demo en vivo

En la EC2 (`ssh -i buildcorp.pem ubuntu@100.60.151.204`):

```bash
systemctl status buildcorp nginx postgresql --no-pager      # servicios activos
sudo ss -tlnp                                               # qué escucha en qué puerto
crontab -l                                                  # tareas programadas
tail -5 ~/buildcorp-deploy.log                              # últimos despliegues
journalctl -u buildcorp -n 30 --no-pager                    # logs de Gunicorn/Django
sudo nginx -t                                               # revisar configuración de Nginx

cd ~/BuildCorp && source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=buildcorp.settings.prod
python manage.py revisar_morosidad                          # correr la tarea a mano
python manage.py showmigrations | head                      # migraciones aplicadas
sudo -u postgres psql buildcorp -c "select codigo, estado from activos_activo limit 5;"
```

Demostraciones rápidas en la web:

1. Entrar como **ventas** → *Nuevo arriendo* → poner devolución anterior a la entrega → aparece el error.
2. Mostrar un **contratista bloqueado**: no aparece seleccionable al crear un arriendo.
3. Entrar como **encargado** y abrir **Cobros** → 403 (permisos por rol).
4. Abrir `/api/v1/` con sesión: la API navegable de DRF.
5. Abrir `/admin/` como **admin**: el admin personalizado.

---

## 15. Glosario

| Término | Significado |
|---|---|
| **AMI** | Imagen del sistema operativo con que arranca una EC2 |
| **API REST** | Interfaz para que programas intercambien datos (JSON) usando URLs y métodos HTTP (GET, POST…) |
| **CSRF** | Ataque donde otra página envía formularios en tu nombre; se evita con un token por sesión |
| **EBS** | Disco virtual de una EC2 |
| **EC2** | Máquina virtual en AWS |
| **Gunicorn** | Servidor WSGI que ejecuta Django con varios procesos |
| **HSTS** | Cabecera que obliga al navegador a usar HTTPS |
| **Idempotente** | Que ejecutarlo dos veces da el mismo resultado (p. ej. `crear_alerta` no duplica alertas abiertas) |
| **Let's Encrypt** | Autoridad que emite certificados TLS gratuitos |
| **Migración** | Archivo que describe un cambio en la estructura de la base de datos |
| **Nginx** | Servidor web y proxy inverso |
| **ORM** | Capa que traduce clases Python a tablas SQL |
| **Proxy inverso** | Intermediario del lado del servidor que reenvía peticiones a la app |
| **Security Group** | Firewall de una instancia EC2 |
| **Serializer** | Convierte objetos ↔ JSON y valida datos (DRF) |
| **Singleton** | Modelo con una sola fila (`ParametroSistema`) |
| **SSH** | Protocolo para abrir una terminal remota cifrada |
| **sslip.io** | DNS gratuito que traduce un nombre a la IP que contiene |
| **systemd** | Administrador de servicios de Linux |
| **TLS** | Protocolo de cifrado de HTTPS |
| **Transacción atómica** | Conjunto de operaciones que se aplica completo o no se aplica |
| **WSGI** | Estándar que conecta un servidor web con una app Python |

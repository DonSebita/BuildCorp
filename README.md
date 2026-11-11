# BuildCorp · Control de arriendo de herramientas y maquinaria ligera

Sistema **interno** de BuildCorp para controlar el arriendo de maquinaria a contratistas: catálogo con trazabilidad, entregas y devoluciones con **firma digital**, **mantenimiento preventivo** automático, **cobros en CLP** y **bloqueo automático de morosos**.

Hecho con **Django 6 + Django REST Framework + PostgreSQL**, desplegado en una **EC2 de AWS Academy** con Nginx, Gunicorn y HTTPS.

| | |
|---|---|
| **App en producción (HTTPS)** | https://100-60-151-204.sslip.io/ |
| **Acceso por IP (HTTP)** | http://100.60.151.204/ |
| **Usuarios demo** | `admin` · `bodeguero` · `encargado` · `ventas` |
| **Contraseña demo** | `buildcorp2026` (también en el botón **?** del login) |

> En AWS Academy la IP pública cambia si se reinicia el laboratorio. Si los enlaces no responden, revisa la IP vigente en la consola de EC2.

![Dashboard del administrador](docs/img/10-dashboard-admin.png)

---

## Índice

1. [El problema](#1-el-problema)
2. [Qué hace el sistema](#2-qué-hace-el-sistema)
3. [Roles](#3-roles)
4. [Recorrido por la aplicación](#4-recorrido-por-la-aplicación)
5. [Reglas de negocio](#5-reglas-de-negocio)
6. [Arquitectura](#6-arquitectura)
7. [API REST](#7-api-rest)
8. [Cómo se desarrolló](#8-cómo-se-desarrolló)
9. [Ejecutar en local](#9-ejecutar-en-local)
10. [Despliegue en AWS EC2](#10-despliegue-en-aws-ec2)
11. [Estructura del repositorio](#11-estructura-del-repositorio)

---

## 1. El problema

BuildCorp arrienda herramientas y maquinaria ligera (rotomartillos, generadores, compactadoras, andamios…) a constructoras y subcontratistas que trabajan en distintas obras. Antes del sistema tenía cuatro problemas:

| Problema | Cómo lo resuelve BuildCorp |
|---|---|
| Se perdían equipos y nadie sabía dónde estaban | Cada máquina tiene un **código único + QR** y una **hoja de vida** con todos sus cambios de estado, préstamos y traslados |
| Los cobros a subcontratistas eran inexactos | El cobro se calcula solo, en **CLP**, por día y mes, con recargo por atraso, daños e IVA. Las tarifas quedan **congeladas** al crear el arriendo |
| Fallas mecánicas imprevistas | **Mantenimiento preventivo** por usos, horas de horómetro o días. Si un equipo llega a su límite, pasa solo a mantenimiento y no se puede entregar |
| Contratistas que no devolvían a tiempo | Una tarea diaria marca los **atrasos**, genera alertas y **bloquea** al contratista después de los días de gracia |

Es **software interno**: no es una tienda en línea y los clientes no tienen cuenta. El responsable de obra firma en la tablet o el celular del encargado de entrega.

## 2. Qué hace el sistema

| Requerimiento | Implementación |
|---|---|
| **RF1** Catálogo con estados y trazabilidad | Estados `Disponible → En uso → Mantenimiento → Dado de baja`, código `RTM-0004` autogenerado, QR, historial de estados y traslados entre bodegas |
| **RF2** Entrega y devolución con firma digital | Firma en `<canvas>` (signature_pad) guardada como PNG con **hash SHA-256**, IP y fecha; no se puede editar |
| **RF3** Mantenimiento preventivo | Plan por **usos**, **horas** o **días** (gana el primero). Folio `MNT-AAAA-NNNN` por mantención |
| **RF4** Morosidad y bloqueo automático | Comando `revisar_morosidad` (cron diario). Solo el Administrador desbloquea y debe dejar el motivo |
| **RT1–RT3** Django + DRF, admin personalizado, permisos por rol | API en `/api/v1/`, Django Admin con badges, inlines y acciones masivas, permisos por grupo |
| **RT4** PostgreSQL + migraciones | PostgreSQL 18 en la misma EC2, migraciones del ORM |
| **RT5** Frontend responsivo con fetch | Templates + Bootstrap 5 + JS vanilla que consume la API (cotización en vivo, entregas, devoluciones, dashboard) |
| **RT6** Despliegue en una EC2 | Nginx + Gunicorn + systemd + cron + HTTPS con Let's Encrypt + despliegue automático desde GitHub |

## 3. Roles

Cada rol trabaja en su propia "copia del talonario", con su color y su dashboard:

| Rol | Qué hace | Qué ve al entrar |
|---|---|---|
| **Administrador** | Todo. Desbloquea contratistas, da de baja activos, configura parámetros, Django Admin | Atrasos, bloqueados, cobros pendientes, solicitudes por aprobar |
| **Ventas** | Contratistas y obras, crea los arriendos, arma paquetes, cobra | Préstamos que vencen, cobros, bloqueados, facturación mensual |
| **Bodeguero** | Registra activos, traslados, mantenciones, imprime etiquetas QR | Mantenciones vencidas y próximas, equipos en taller |
| **Encargado E/R** | Entrega y recibe en terreno: checklist, horómetro, firma | Entregas por hacer y devoluciones esperadas (pensado para tablet) |

**Separación de funciones:** Ventas *crea* el arriendo pero no entrega ni recibe los equipos; eso lo hace el Encargado E/R. Nadie controla el proceso completo por sí solo.

![Login con ayuda de credenciales](docs/img/02-login-credenciales.png)

## 4. Recorrido por la aplicación

### Ventas: nuevo arriendo con cotización en vivo

Se elige contratista, obra, fechas y paquetes o equipos sueltos. La cotización en CLP se recalcula con `fetch` a `/api/v1/prestamos/cotizar/` sin guardar nada. Los paquetes sin stock y los contratistas bloqueados aparecen deshabilitados.

![Nuevo arriendo](docs/img/24-nuevo-arriendo.png)

Si la devolución pactada es anterior a la entrega, el servidor rechaza la cotización:

![Error de fechas](docs/img/25-error-fecha-devolucion.png)

### Encargado E/R: entrega y devolución en terreno

Pantallas pensadas para tablet. En la devolución se marca el estado de llegada de cada equipo (bueno, desgaste, dañado o faltante), el horómetro y el cargo por daño, y el responsable de obra firma.

| Entrega | Devolución |
|---|---|
| ![Entrega](docs/img/41-entrega.png) | ![Devolución](docs/img/42-devolucion.png) |

### Cobro y comprobante

Al confirmar la devolución se genera el cobro: arriendo + recargo por atraso + daños + IVA. Ventas registra el pago y el préstamo queda cerrado. El comprobante incluye las firmas y se imprime desde el navegador.

| Cobro | Comprobante |
|---|---|
| ![Cobro](docs/img/27-cobro.png) | ![Comprobante](docs/img/28-comprobante.png) |

### Bodeguero: catálogo, hoja de vida y mantenimiento

| Catálogo | Hoja de vida de un activo |
|---|---|
| ![Catálogo](docs/img/31-catalogo.png) | ![Ficha](docs/img/32-ficha-activo.png) |

| Mantenimiento | Etiquetas QR |
|---|---|
| ![Mantenimiento](docs/img/33-mantenimiento.png) | ![Etiquetas](docs/img/35-etiquetas.png) |

### Contratistas, paquetes y bloqueo

| Contratistas | Contratista bloqueado |
|---|---|
| ![Contratistas](docs/img/21-contratistas.png) | ![Bloqueado](docs/img/22-contratista-bloqueado.png) |

![Paquetes de maquinaria](docs/img/23-paquetes.png)

### Administración

| Django Admin personalizado | API navegable de DRF |
|---|---|
| ![Admin](docs/img/13-admin-prestamos.png) | ![API](docs/img/14-api-navegable.png) |

## 5. Reglas de negocio

### Ciclo de vida de un activo

```
              ┌────────────── entrega ──────────────┐
              │                                     ▼
 [Alta] ─► DISPONIBLE ◄──── devolución OK ──── EN_USO
              │   ▲                                 │
   envío a    │   │ mantención                      │ devolución con daño
   mantención ▼   │ finalizada                      │ o umbral alcanzado
           MANTENIMIENTO ◄──────────────────────────┘
              │
              │ baja (solo Administrador, con motivo)
              ▼
         DADO_DE_BAJA  (final: no vuelve a prestarse)
```

Los estados cambian **solo** desde la capa de servicios (`cambiar_estado`), que valida la transición y deja registro en la hoja de vida.

### Cobro en CLP

```
días      = (devolución real − entrega), mínimo 1
arriendo  = días × diaria                                   si días < 30
          = meses × mensual + min(resto × diaria, mensual)  si días ≥ 30
atraso    = días de atraso × diaria × 50 %
neto      = arriendo + atraso + daños
total     = neto + IVA (19 %)
```

Ejemplo: Kit Compactación ($60.000/día, $1.100.000/mes) por 45 días → 1 × $1.100.000 + min(15 × $60.000, $1.100.000) = **$2.000.000 neto**, $2.380.000 con IVA.

### Mantenimiento preventivo

Cada categoría define cada cuántos **usos**, **horas** o **días** se mantiene el equipo (gana el que ocurra primero). Al devolver un equipo se suma 1 uso y las horas del horómetro; si llegó al límite pasa solo a `MANTENIMIENTO`. Un equipo vencido no se puede entregar.

### Morosidad

Cada día, `revisar_morosidad` marca como **atrasados** los préstamos que pasaron su fecha pactada y avisa a Ventas. Si el atraso supera los **3 días de gracia** (configurable), el contratista queda **bloqueado** y no se le puede crear ni entregar otro arriendo hasta que el Administrador lo desbloquee con un motivo.

## 6. Arquitectura

```
Navegador (Templates + JS fetch)
        │  HTTPS :443 / HTTP :80
        ▼
     Nginx  ── sirve /static y /media, termina TLS (Let's Encrypt)
        │  proxy_pass 127.0.0.1:8000
        ▼
    Gunicorn (3 workers, systemd) ── Django + DRF
        │
        ▼
   PostgreSQL 18 (solo localhost:5432)

   cron (diario)       ─► revisar_morosidad / revisar_mantenimientos
   systemd timer (2 m) ─► deploy/actualizar.sh (despliegue automático desde GitHub)
```

Todo corre en **una sola instancia EC2** (t3.small, Ubuntu 26.04).

| Capa | Tecnología |
|---|---|
| Backend | Python 3.14, Django 6, Django REST Framework, django-filter |
| Base de datos | PostgreSQL 18 (`psycopg`) |
| Autenticación | Sesiones de Django; DRF con `SessionAuthentication` y CSRF |
| Frontend | Django Templates, Bootstrap 5, JS vanilla (`fetch`), Chart.js |
| Firma | signature_pad sobre `<canvas>` → PNG + SHA-256 |
| QR | `qrcode` (generación al vuelo) y `html5-qrcode` (escaneo) |
| Configuración | `django-environ` con `.env` |
| Servidor | Nginx, Gunicorn, systemd, cron, certbot |

**Decisiones de diseño clave**

- **Capa de servicios** (`services.py`): toda la lógica de negocio vive ahí, no en las vistas. Así la usan igual las pantallas, la API y el admin.
- **`transaction.atomic()` + `select_for_update()`** en entregas, devoluciones y correlativos para que dos usuarios no tomen el mismo equipo o el mismo folio a la vez.
- **Precios congelados**: el préstamo copia las tarifas vigentes; cambiar una tarifa no altera arriendos existentes.
- **Montos en enteros**: el CLP no tiene decimales, así que no hay errores de redondeo con `float`.
- **QR al vuelo**: el QR no se guarda como imagen; si cambia la IP solo hay que reimprimir.

## 7. API REST

Base `/api/v1/`, autenticación por sesión y permisos por rol (`apps/usuarios/permissions.py`).

| Recurso | Endpoints principales |
|---|---|
| Activos | `GET/POST /activos/`, `POST /activos/{id}/cambiar-estado/`, `GET /activos/{id}/hoja-vida/`, `POST /activos/{id}/trasladar/`, `GET /activos/codigo/{codigo}/`, `GET /activos/{id}/qr/` |
| Paquetes | `/paquetes/`, `GET /paquetes/{id}/disponibilidad/` |
| Contratistas y obras | `/contratistas/`, `POST /contratistas/{id}/desbloquear/`, `/obras/` |
| Préstamos | `/prestamos/`, `POST /prestamos/cotizar/`, `POST /prestamos/{id}/asignar-activos/`, `POST /prestamos/{id}/entregar/`, `POST /prestamos/{id}/devolver/`, `GET /prestamos/atrasados/` |
| Cobros | `/cobros/`, `POST /cobros/{id}/pagar/` |
| Mantenimiento | `/mantenimientos/`, `/planes-mantenimiento/proximos/` |
| Alertas | `/alertas/`, `POST /alertas/{id}/marcar-leida/` |
| Dashboard | `GET /dashboard/resumen/` |

Los errores de negocio responden **400** con un mensaje legible (`{"detail": "La devolución pactada no puede ser anterior a la entrega."}`) y los de permisos **403**.

## 8. Cómo se desarrolló

El proyecto se planificó primero en [PLANIFICACION.md](PLANIFICACION.md) (alcance, roles, modelo de datos, reglas de cobro y fases) y luego se construyó por fases, cada una con un entregable verificable:

| Fase | Contenido |
|---|---|
| 0. Setup | Proyecto Django, PostgreSQL, settings por entorno (`base`/`dev`/`prod`) y `.env` |
| 1. Usuarios y roles | Usuario propio (`AbstractUser`), grupos, login y menú según rol |
| 2. Activos (RF1) | Modelos, máquina de estados, historial, bodegas, traslados, paquetes, código + QR |
| 3. Contratistas y obras | CRUD, estado de bloqueo |
| 4. Préstamos y firma (RF2) | Cotización, entrega y devolución con firma, cobro en CLP, comprobante |
| 5. Mantenimiento (RF3) | Planes por usos/horas/días, paso automático a mantenimiento |
| 6. Alertas y morosidad (RF4) | Alertas por rol, comandos diarios, bloqueo y desbloqueo |
| 7. Dashboard | KPIs por rol, gráfico de estados, exportación CSV |
| 8. Admin y pulido | Admin personalizado, diseño responsivo, tests, datos demo |
| 9. Despliegue | EC2, Nginx, Gunicorn, cron, HTTPS y despliegue automático |

El diseño visual ("talonario de arriendo", un color por rol) está documentado en [DESIGN.md](DESIGN.md) y [PRODUCT.md](PRODUCT.md). El uso de IA durante el desarrollo quedó registrado en [prompts_ia.md](prompts_ia.md).

**Pruebas:** `python manage.py test apps` cubre el cálculo en CLP (menos de 30 días, 45 días, tope del resto, mínimo 1 día) y el flujo completo por API: crear → entregar con firma → devolver → cobro, el paso automático a mantenimiento por usos y el bloqueo por morosidad.

## 9. Ejecutar en local

Requisitos: Python 3.12+ y PostgreSQL 16+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    ·    Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # completa DATABASE_URL, SECRET_KEY y DEBUG=True
```

Crear la base en PostgreSQL (una vez):

```sql
CREATE USER buildcorp WITH PASSWORD 'tu_clave';
CREATE DATABASE buildcorp OWNER buildcorp;
```

```bash
python manage.py migrate
python manage.py cargar_demo          # roles, usuarios, ~34 activos, paquetes, préstamos y firmas de ejemplo
python manage.py runserver
```

Abrir `http://127.0.0.1:8000/`. Para recargar la demo desde cero: `python manage.py cargar_demo --reset`.

Tareas diarias (en producción las corre cron):

```bash
python manage.py revisar_morosidad
python manage.py revisar_mantenimientos
```

Pruebas: `python manage.py test apps`

## 10. Despliegue en AWS EC2

1. Lanzar una EC2 Ubuntu (t3.small). Security Group: **22** (SSH, tu IP), **80** y **443** (0.0.0.0/0).
2. Conectarse por SSH y clonar el repositorio en `/home/ubuntu/BuildCorp`.
3. Ejecutar:
   ```bash
   cd /home/ubuntu/BuildCorp
   sudo bash deploy/setup_ec2.sh <IP_PUBLICA>
   ```
   El script instala PostgreSQL, Nginx y Python; crea la base y el `.env`; aplica migraciones; carga la demo; y configura Gunicorn (`systemd`), Nginx, el `crontab` y el despliegue automático.
4. Abrir `http://<IP_PUBLICA>/`.

**HTTPS:** certificado de Let's Encrypt para `<ip-con-guiones>.sslip.io` (un DNS gratuito que apunta a la IP), con renovación automática por `certbot.timer`. La cámara en vivo del escáner QR solo funciona con HTTPS; por HTTP se usa «Tomar foto del QR».

**Despliegue automático:** basta con hacer `git push` a `main`. En la EC2, el timer `buildcorp-actualizar.timer` revisa GitHub cada 2 minutos y, si hay commits nuevos, ejecuta [`deploy/actualizar.sh`](deploy/actualizar.sh) (`git pull`, dependencias si cambió `requirements.txt`, `migrate`, `collectstatic` y reinicio de Gunicorn). El historial queda en `/home/ubuntu/buildcorp-deploy.log`; para forzarlo a mano: `sudo bash deploy/actualizar.sh`. Los cambios al `.env` se hacen en el servidor.

**Si la IP cambia:** editar `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `SITE_URL` en `.env` y ejecutar `sudo systemctl restart buildcorp`. Los QR se generan al vuelo con la URL vigente; basta con reimprimir las etiquetas.

## 11. Estructura del repositorio

```
buildcorp/settings/{base,dev,prod}.py   configuración por entorno (django-environ)
apps/usuarios       usuario propio, roles (Grupos), permisos DRF, login, cargar_demo
apps/activos        categorías, bodegas, activos, historial, traslados, paquetes, QR
apps/contratistas   contratistas, obras, bloqueo y desbloqueo
apps/prestamos      préstamos, firmas, cobros CLP, parámetros del sistema
apps/mantenimiento  planes por usos/horas/días y registros con folio
apps/alertas        alertas por rol + comandos revisar_morosidad / revisar_mantenimientos
apps/dashboard      dashboard por rol (API /api/v1/dashboard/resumen/) y exportación CSV
templates/, static/ interfaz (Bootstrap 5 + CSS propio, JS vanilla con fetch, Chart.js)
deploy/             Nginx, Gunicorn, crontab, instalación y despliegue automático
docs/img/           capturas de pantalla
```

Cada app separa `models.py` (datos), `services.py` (reglas de negocio), `views.py` (pantallas), `api.py` + `serializers.py` (API REST) y `admin.py` (Django Admin).

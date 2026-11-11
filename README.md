# BuildCorp · Control de arriendo de herramientas y maquinaria ligera

Software **interno** de BuildCorp para controlar préstamos, bodegas, hojas de vida de equipos, mantenimiento preventivo y cobros en CLP. Los contratistas no tienen cuenta: el responsable de obra firma en el dispositivo del encargado al entregar y al devolver.

**URL pública (EC2):** `http://<IP_PUBLICA>/` ← actualizar antes de la evaluación (en AWS Academy la IP cambia al reiniciar el laboratorio).

| Usuario demo | Rol | Qué ve al entrar |
|---|---|---|
| `admin` | Administrador | Atrasos, bloqueados, cobros pendientes, solicitudes por aprobar, Django Admin |
| `bodeguero` | Bodeguero | Mantenciones vencidas y próximas, equipos en taller, inventario por estado |
| `encargado` | Encargado de entrega/recepción | Entregas por hacer y devoluciones esperadas (pensado para tablet) |
| `ventas` | Ventas | Préstamos que vencen, cobros por cobrar, contratistas bloqueados, facturación mensual |

Contraseña de todos los usuarios demo: `buildcorp2026`

## Requerimientos cubiertos

| # | Dónde |
|---|---|
| RF1 Catálogo con estados y trazabilidad | `apps/activos` · ficha con hoja de vida y línea de estados · código `RTM-0004` + QR |
| RF2 Entrega y devolución con firma digital | `apps/prestamos` · pantallas de entrega/devolución con `signature_pad`, firma con hash SHA-256, IP y fecha |
| RF3 Mantenimiento preventivo por usos, horas o fecha | `apps/mantenimiento` · paso automático a MANTENIMIENTO al devolver · folio `MNT-AAAA-NNNN` |
| RF4 Morosidad y bloqueo automático | `manage.py revisar_morosidad` (cron) · desbloqueo solo por el Administrador con motivo |
| RT1–RT3 Django + DRF, admin personalizado, permisos por rol | `apps/*/api.py`, `apps/*/admin.py`, `apps/usuarios/permissions.py` |
| RT4 PostgreSQL + migraciones | `DATABASE_URL` en `.env`, migraciones en `apps/*/migrations` |
| RT5 Frontend responsivo con fetch | `static/js/api.js`, `dashboard.js`, listas, nuevo arriendo, entrega y devolución |
| RT6 Despliegue en una EC2 | `deploy/setup_ec2.sh`, Nginx + Gunicorn + cron |

API REST en `/api/v1/` (navegable con sesión iniciada). Documentación del diseño en [PLANIFICACION.md](PLANIFICACION.md), [PRODUCT.md](PRODUCT.md) y [DESIGN.md](DESIGN.md).

## Ejecutar en local (Windows / Linux)

Requisitos: Python 3.12+ y PostgreSQL 16+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    ·    Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # y completa DATABASE_URL, SECRET_KEY, DEBUG=True
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

## Despliegue en AWS EC2 (AWS Academy)

1. Lanzar una EC2 Ubuntu 24.04 (t2.micro o t3.small). Security Group: puerto **22** (tu IP) y **80** (0.0.0.0/0).
2. Conectarse por SSH y clonar el repositorio en `/home/ubuntu/BuildCorp`.
3. Ejecutar:
   ```bash
   cd /home/ubuntu/BuildCorp
   sudo bash deploy/setup_ec2.sh <IP_PUBLICA>
   ```
   El script instala PostgreSQL, Nginx y Python; crea la base, el `.env`, aplica migraciones, carga la demo y configura Gunicorn (`systemd`), Nginx y el `crontab`.
4. Abrir `http://<IP_PUBLICA>/` y anotar la IP arriba en este README.

**Despliegue automático:** basta con hacer `git push` a `main`. En la EC2, el timer `buildcorp-actualizar.timer` revisa GitHub cada 2 minutos y, si hay commits nuevos, ejecuta [`deploy/actualizar.sh`](deploy/actualizar.sh) (`git pull`, dependencias si cambió `requirements.txt`, `migrate`, `collectstatic` y reinicio de Gunicorn). El historial queda en `/home/ubuntu/buildcorp-deploy.log`; para forzarlo a mano: `sudo bash deploy/actualizar.sh`. Los cambios al `.env` siguen haciéndose en el servidor.

Si la IP cambia: editar `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `SITE_URL` en `.env`, luego `sudo systemctl restart buildcorp`. Los QR se generan al vuelo con la IP vigente; basta con reimprimir las etiquetas.

> La cámara en vivo del navegador requiere HTTPS. Con `http://<IP>` el escáner usa **«Tomar foto del QR»**, que funciona sin HTTPS, y siempre se puede escribir el código.

## Estructura

```
buildcorp/settings/{base,dev,prod}.py   configuración por entorno (django-environ)
apps/usuarios       usuario custom, roles (Grupos), permisos DRF, login, cargar_demo
apps/activos        categorías, bodegas, activos, historial, traslados, paquetes, QR
apps/contratistas   contratistas, obras, bloqueo y desbloqueo
apps/prestamos      préstamos, firmas, cobros CLP, parámetros del sistema
apps/mantenimiento  planes por usos/horas/días y registros con folio
apps/alertas        alertas por rol + comandos revisar_morosidad / revisar_mantenimientos
apps/dashboard      dashboard por rol (API /api/v1/dashboard/resumen/) y exportación CSV
templates/, static/ interfaz (Bootstrap 5 + CSS propio, JS vanilla con fetch, Chart.js)
deploy/             Nginx, Gunicorn, crontab y script de instalación
```

El uso de IA durante el desarrollo está registrado en [prompts_ia.md](prompts_ia.md).

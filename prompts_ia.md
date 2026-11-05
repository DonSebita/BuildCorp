# Registro de uso de Inteligencia Artificial

Este archivo registra las consultas y la ayuda pedida a herramientas de IA durante el desarrollo del proyecto **BuildCorp: Sistema de Alquiler y Control de Herramientas**, como exige la rúbrica.

| Campo | Valor |
|---|---|
| Herramienta | Claude Code (extensión de VS Code) |
| Modelo | Claude Opus 5.5 (Anthropic) |
| Uso general | Planificación, generación de estructura de código, HTML/CSS y scripts de despliegue |

> Cada entrada indica la fecha, el prompt del estudiante (resumido o textual), la respuesta o el apoyo que entregó la IA y los archivos que se crearon o modificaron.

---

## Registro

### #1 · 2026-11-05 · Planificación inicial del proyecto

**Prompt:**
> Tengo que realizar una aplicación para una tienda de arriendo de maquinaria llamada BuildCorp. Antes de comenzar quiero realizar una planificación de lo que se necesita como guía para la realización del proyecto. De momento tengo 3 roles: el bodeguero, el que revisa la recepción y entrega de máquinas arrendadas y el administrador, quizás ventas. *(Se adjuntó el enunciado del proyecto y los requerimientos técnicos de la rúbrica.)* Primero crea el .md que va a funcionar para la estructura del proyecto. NO va a ser una página donde los clientes puedan arrendar maquinaria, sino un software interno para la empresa.

**Apoyo de la IA:**
- Creó un documento de planificación con el alcance, los roles y la matriz de permisos, los flujos (ciclo de estados del activo, entrega, devolución, morosidad y mantenimiento), el modelo de datos, la arquitectura, la estructura del repositorio, los endpoints de la API, las pantallas, la personalización de Django Admin, la seguridad, el despliegue en EC2, las fases de trabajo y un checklist de entrega.
- Propuso usar cron con management commands de Django para las tareas automáticas (en lugar de Celery) y signature_pad para la firma digital.

**Archivos:** `PLANIFICACION.md` (creado)

---

### #2 · 2026-11-05 · Registro de IA e incorporación del rol Ventas

**Prompt:**
> Crea el archivo de IA que se pide en la rúbrica, donde se anote siempre lo que se escriba en la conversación, y sí quiero añadir ventas, para que modifiques la planificación.

**Apoyo de la IA:**
- Creó este archivo `prompts_ia.md` con el formato de registro y las entradas anteriores.
- Agregó un `CLAUDE.md` para que en las sesiones siguientes la IA siga registrando aquí cada prompt.
- Actualizó `PLANIFICACION.md` para que **Ventas** sea un rol definitivo: agregó responsabilidades, filas nuevas en la matriz de permisos y la decisión pendiente resuelta.

**Archivos:** `prompts_ia.md` (creado), `CLAUDE.md` (creado), `PLANIFICACION.md` (modificado)

---

### #3 · 2026-11-05 · Cobro en CLP, paquetes de maquinaria y mantención por usos

**Prompt:**
> Unidad de cobro en peso chileno y que sea por día y mes. También hay que crear los paquetes de maquinaria que se arriendan, por ejemplo, a una constructora. También, después de varios usos que definas tú, que se vaya a mantención.

**Apoyo de la IA:**
- Definió las reglas de cobro en CLP (enteros, sin decimales): tarifa diaria y mensual por categoría y por paquete, cálculo de meses y días con tope, recargo por atraso, IVA 19 %, precios congelados al crear el préstamo y la configuración regional `es-cl`.
- Diseñó los **paquetes de maquinaria** (definidos por categoría y cantidad, con asignación de activos concretos al entregar) y propuso 4 paquetes de ejemplo.
- Propuso umbrales de mantención por **usos** (8, 10, 15 o 20 según el tipo de equipo), combinados con horas y días, y el paso automático a MANTENIMIENTO al devolver.
- Actualizó en la planificación el modelo de datos, la API, las pantallas, los permisos, las fases, los datos semilla y las decisiones pendientes.

**Archivos:** `PLANIFICACION.md` (modificado), `prompts_ia.md` (modificado)

---

### #4 · 2026-11-05 · Identificador único por máquina para la mantención

**Prompt:**
> ¿Se puede hacer un sistema en que cada máquina tenga su identificador para la mantención?

**Apoyo de la IA:**
- Propuso un esquema de identificación: código interno autogenerado e inmutable (prefijo de la categoría + correlativo, por ejemplo `RTM-0004`), número de serie del fabricante y código QR impreso en una etiqueta.
- Definió el escaneo del QR con la cámara del celular y dentro de la app (`html5-qrcode`) para entregas, devoluciones y mantenciones.
- Agregó un folio único por mantención (`MNT-AAAA-NNNN`) y el flujo del bodeguero: escanear, ver la ficha y registrar la mantención.
- Actualizó el modelo de datos, la API, las pantallas, el stack y las fases en la planificación.

**Archivos:** `PLANIFICACION.md` (modificado), `prompts_ia.md` (modificado)

---

### #5 · 2026-11-05 · Construcción del proyecto con diseño empresarial y dashboards por rol

**Prompt:**
> Quiero que crees el proyecto de BuildCorp siguiendo las instrucciones dadas, quiero un diseño empresarial y fácil de usar, con dashboards que muestren diferente información según el rol del usuario. *(Se usó la skill de diseño «impeccable». Respuestas a las preguntas de la IA: el estudiante entrega la clave de PostgreSQL; no hay logo ni colores definidos; 3 días de gracia y comprobante HTML imprimible. Eligió la dirección visual «Talonario de arriendo».)*

**Apoyo de la IA:**
- Propuso direcciones visuales en una página de decisión; el estudiante eligió «Talonario de arriendo» (folios rojos, estados como timbres, una copia de color por rol).
- Generó el proyecto Django 6 + DRF completo: 7 apps con modelos, migraciones, capa de servicios (estados, cobro CLP, entrega/devolución con firma y hash SHA-256, mantención por usos/horas/días, morosidad y bloqueo), API REST con permisos por rol y Django Admin personalizado (badges, inlines, acciones masivas, vista previa de firmas).
- Creó la interfaz con plantillas, Bootstrap 5, CSS propio y JS con fetch: dashboard distinto para cada rol, catálogo con filtros, ficha con hoja de vida y línea de estados, nuevo arriendo con cotización en vivo, entrega/devolución para tablet con escáner QR y firma, comprobante imprimible, cobros, mantenimiento, bodegas, paquetes, etiquetas QR y alertas.
- Agregó el comando `cargar_demo`, los comandos de cron, 8 pruebas automatizadas, los archivos de despliegue en EC2 (Nginx, Gunicorn, crontab, `setup_ec2.sh`), README, PRODUCT.md y DESIGN.md.
- Verificó el ciclo completo en el navegador (crear → asignar → firmar → entregar → devolver con daño → pagar) y revisó capturas en escritorio y celular, corrigiendo el riel invisible, las tablas en móvil y la disponibilidad de paquetes.

**Archivos:** `manage.py`, `requirements.txt`, `.env.example`, `.gitignore`, `README.md`, `PRODUCT.md`, `DESIGN.md`, `buildcorp/`, `apps/`, `templates/`, `static/`, `deploy/` (creados); `PLANIFICACION.md` (modificado: Django 6, QR al vuelo, decisiones resueltas, sección de diseño), `prompts_ia.md` (modificado)

---

### #6 · 2026-11-05 · Cambio de SQLite a PostgreSQL

**Prompt:**
> Cambiemos a PostgreSQL. *(El estudiante entregó la clave del superusuario `postgres`; se omite por seguridad.)*

**Apoyo de la IA:**
- Creó en PostgreSQL 18 un usuario `buildcorp` con clave aleatoria y la base `buildcorp`, y configuró `DATABASE_URL` en `.env` (no versionado).
- Aplicó las migraciones y cargó la demo en PostgreSQL.
- Corrigió un error que SQLite ocultaba: `SELECT ... FOR UPDATE` no se puede combinar con joins opcionales en PostgreSQL; ahora se bloquea solo la fila del activo (`select_for_update(of=("self",))`).
- Volvió a pasar las 8 pruebas y el flujo completo en el navegador sobre PostgreSQL.

**Archivos:** `.env` (modificado, no versionado), `apps/prestamos/services.py` (modificado), `prompts_ia.md` (modificado)

---

### #7 · 2026-11-05 · Instalación de graphifyy con uv

**Prompt:**
> uv tool install graphifyy

**Apoyo de la IA:**
- Intentó ejecutar `uv tool install graphifyy`; falló porque `uv` no está instalado en el sistema.
- Verificó que solo existe el Python del `.venv` del proyecto y propuso opciones para instalar `uv` o usar `pip`.

**Archivos:** `prompts_ia.md` (modificado)

---

### #8 · 2026-11-05 · Instalación de uv y graphifyy

**Prompt:**
> sí, instala uv con la opción 1

**Apoyo de la IA:**
- Instaló `uv` 0.13.7 con el instalador oficial de Astral en `C:\Users\hp\.local\bin` (ya incluido en el PATH de usuario).
- Ejecutó `uv tool install graphifyy` (v0.9.102), que dejó disponibles los comandos `graphify` y `graphify-mcp`, y verificó que `graphify` responde.

**Archivos:** `prompts_ia.md` (modificado)

---

### #9 · 2026-11-05 · graphify como skill de Claude Code

**Prompt:**
> sí, instálalo como skill de Claude

**Apoyo de la IA:**
- Ejecutó `graphify install --platform claude`: copió la skill a `~/.claude/skills/graphify/` (SKILL.md y references) y la registró en el `CLAUDE.md` global del usuario.
- Explicó que se usa escribiendo `/graphify .` en una sesión nueva de Claude Code.

**Archivos:** `prompts_ia.md` (modificado); fuera del proyecto: `~/.claude/skills/graphify/` (creado), `~/.claude/CLAUDE.md` (modificado por el instalador)

---

### #10 · 2026-11-05 · Grafo de conocimiento del proyecto con graphify

**Prompt:**
> /graphify .

**Apoyo de la IA:**
- Ejecutó el pipeline de graphify sobre el proyecto: 155 archivos (117 de código, 37 documentos/plantillas, 1 imagen).
- Extracción AST del código (684 nodos) y extracción semántica de docs y plantillas con 4 subagentes en paralelo (181 nodos), con cobertura completa de cada archivo.
- Generó un grafo de 912 nodos, 1921 aristas y 90 comunidades, etiquetó las comunidades en español y exportó `graph.html`, `graph.json` y `GRAPH_REPORT.md`.

**Archivos:** `graphify-out/` (creado), `prompts_ia.md` (modificado)

---

### #11 · 2026-11-05 · Subir el proyecto a GitHub

**Prompt:**
> sube todo a github, crea el repositorio

**Apoyo de la IA:**
- Revisó el estado: el proyecto aún no es un repositorio git, `git` está instalado pero falta la CLI `gh` de GitHub, y `.gitignore` ya excluye `.env`, `.venv/` y `db.sqlite3`.
- Consultó al usuario el nombre, la visibilidad del repositorio y cómo autenticarse antes de publicar.

**Archivos:** `prompts_ia.md` (modificado)

---

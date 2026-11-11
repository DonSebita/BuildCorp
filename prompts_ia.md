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
- (cont. #11) El usuario eligió repositorio **público** `buildcorp`, incluir `graphify-out/` completo e instalar `gh`. La IA instaló GitHub CLI 2.103.3 con winget, inicializó git en `main`, agregó `.gitattributes` (finales LF para que `setup_ec2.sh` funcione en la EC2) y creó el commit inicial (321 archivos, sin `.env`). Queda pendiente que el usuario inicie sesión con `gh auth login` para crear el repositorio y hacer push.

**Archivos:** `.gitattributes` (creado), `prompts_ia.md` (modificado)

---

### #12 · 2026-11-05 · Cómo ver el grafo

**Prompt:**
> como veo el grafo ahora?

**Apoyo de la IA:**
- Abrió `graphify-out/graph.html` en el navegador predeterminado y explicó cómo navegarlo y otras formas de consultarlo.

**Archivos:** `prompts_ia.md` (modificado)

---

### #13 · 2026-11-05 · Consulta al grafo: cómo funciona el arriendo

**Prompt:**
> /graphify como funciona el arriendo de una maquina

**Apoyo de la IA:**
- Consultó el grafo existente (`graphify query`) y recorrió las aristas de llamadas de `apps/prestamos/services.py` y las reglas de negocio (`rationale`) extraídas de `PLANIFICACION.md` y las plantillas.
- Explicó el ciclo completo: cotización, creación del préstamo, asignación de equipos, entrega con firma, devolución, cobro automático, pago, morosidad y paso a mantención.

**Archivos:** `prompts_ia.md` (modificado)

---

### #14 · 2026-11-05 · Usuarios de la aplicación

**Prompt:**
> cuales son los usuarios de la app

**Apoyo de la IA:**
- Revisó `PLANIFICACION.md`, `apps/usuarios/roles.py`, el comando `cargar_demo` y el `README.md`.
- Explicó los cuatro roles internos (Administrador, Bodeguero, Encargado E/R y Ventas), los usuarios demo que crea `cargar_demo` y que los contratistas no tienen cuenta.

**Archivos:** `prompts_ia.md` (modificado)

---

### #15 · 2026-11-05 · Mostrar el grafo de conocimiento

**Prompt:**
> muestra el grafo

**Apoyo de la IA:**
- Abrió `graphify-out/graph.html` (grafo interactivo generado por graphify) en el navegador.
- Resumió las cifras del grafo (912 nodos, 1921 aristas, 90 comunidades) y las principales comunidades desde `GRAPH_REPORT.md`.

**Archivos:** Ninguno (solo consulta)

---

### #16 · 2026-11-11 · Despliegue: ¿Cloudflare o EC2?

**Prompt:**
> necesito pasar a subir el proyecto ahora a cloudflare para seguir con la evaluacion (luego: "tengo una ec2 pero ahora necesito crear otra para esta evaluacion", revisa la pauta y la receta EC2 + Gunicorn + Nginx entregada)

**Apoyo de la IA:**
- Leyó la pauta `EVA_3_Backend.docx` y la receta en PDF del docente.
- Concluyó que la pauta exige una EC2 única de AWS Academy con PostgreSQL + Django y acceso por IP pública; Cloudflare no es requisito (y no puede ejecutar Django + PostgreSQL).
- Comparó la receta con `deploy/setup_ec2.sh`, `gunicorn.service` y `nginx_buildcorp.conf` (mismo esquema Nginx → Gunicorn; el proyecto usa TCP 127.0.0.1:8000 en vez de socket UNIX) y entregó los pasos para levantar la nueva EC2.

**Archivos:** `prompts_ia.md` (modificado)

---

### #17 · 2026-11-11 · Siguiente paso tras crear la EC2

**Prompt:**
> voy aca, asocie la ip elastica y las claves quedaron en el desktop (carpeta claves), ¿qué sigue? (captura de la consola EC2)

**Apoyo de la IA:**
- Revisó la captura: la nueva instancia `buildcorp` (t3.small, IP pública 54.242.14.38) aún aparecía sin IP elástica; la elástica 98.86.195.67 figuraba en la otra instancia (t3.micro).
- Ubicó la clave `buildcorp.pem` en `Desktop\claves` y dio los comandos para protegerla (`icacls`), conectarse por SSH y ejecutar `deploy/setup_ec2.sh`.

**Archivos:** `prompts_ia.md` (modificado)

---

### #18 · 2026-11-11 · Conexión SSH a la nueva EC2

**Prompt:**
> hazlo tú para entrar, actualiza las cosas e instala lo necesario · conéctate a la IP elástica 54.242.14.38 con la clave de Desktop/claves y deja funcionando la página

**Apoyo de la IA:**
- Protegió las claves `.pem` con `icacls` e intentó conectarse por SSH desde PowerShell.
- Diagnosticó: 98.86.195.67 corresponde a la EC2 antigua (clave EdTech); en 54.242.14.38 el puerto 22 cierra la conexión antes del saludo SSH y el puerto 80 no responde, lo que apunta a reglas del Security Group (SSH limitado a la IP de la red anterior y HTTP sin abrir).
- Indicó cómo corregir las reglas de entrada para continuar con la instalación.

**Archivos:** `prompts_ia.md` (modificado)

---

### #19 · 2026-11-11 · Revisión de reglas del Security Group

**Prompt:**
> estas son mis reglas de seguridad (captura: HTTP 80, ICMP y SSH 22 desde 0.0.0.0/0)

**Apoyo de la IA:**
- Confirmó que las reglas son correctas, reintentó SSH/HTTP y probó ping: 54.242.14.38 no responde ni al ping, aunque ICMP está permitido.
- Concluyó que esas reglas no están aplicadas a esa IP: o no se guardaron, o pertenecen a otro Security Group, o la IP pública de la instancia cambió al asociar la IP elástica.

**Archivos:** `prompts_ia.md` (modificado)

---

### #20 · 2026-11-11 · Nueva IP elástica y bloqueo de SSH por la red

**Prompt:**
> ahora sí, la dirección IP es 100.60.151.204

**Apoyo de la IA:**
- Probó la nueva IP: responde al ping, pero SSH se corta antes del saludo, mientras la EC2 antigua sí acepta SSH desde la misma red. También se "abre" un puerto que el Security Group no permite, señal de que la red móvil intercepta el tráfico.
- Propuso dos alternativas: usar la EC2 antigua como puente SSH (requiere la autorización del usuario) o ejecutar la instalación desde EC2 Instance Connect en el navegador.

**Archivos:** `prompts_ia.md` (modificado)

---

### #21 · 2026-11-11 · App desplegada en la nueva EC2

**Prompt:**
> ahora está funcionando 100.60.151.204

**Apoyo de la IA:**
- Intentó verificar `/`, `/admin/` y `/static/` desde el PC; desde la red móvil actual no hubo conexión (la misma red que bloqueaba SSH), por lo que la verificación quedó a cargo del usuario en su navegador.
- Actualizó el README con la URL pública http://100.60.151.204/ y los pasos de despliegue (IP elástica, EC2 Instance Connect).

**Archivos:** `README.md` (modificado), `prompts_ia.md` (modificado)

---

### #22 · 2026-11-11 · HTTPS con Let's Encrypt y Nginx

**Prompt:**
> hay que seguir la receta para tener mi SSL también, Nginx y todo lo que se pide para la evaluación (repo: github.com/DonSebita/BuildCorp)

**Apoyo de la IA:**
- Explicó que Let's Encrypt necesita un dominio y propuso `sslip.io` (`100-60-151-204.sslip.io` resuelve a la IP elástica) sin perder el acceso por IP que exige la pauta.
- Creó `deploy/setup_ssl.sh`: instala certbot, valida por webroot, configura Nginx (HTTP por IP, redirección y bloque 443 con TLS 1.2/1.3 y HSTS), actualiza `.env` (hosts, CSRF, `SITE_URL`) y comprueba la renovación automática.
- Agregó `SECURE_PROXY_SSL_HEADER` en `settings/prod.py`, documentó el paso en README y PLANIFICACION y subió los cambios a GitHub.

**Archivos:** `deploy/setup_ssl.sh` (creado), `buildcorp/settings/prod.py`, `README.md`, `PLANIFICACION.md`, `prompts_ia.md` (modificados)

---

### #23 · 2026-11-11 · Despliegue y SSL hechos directamente en la EC2

**Prompt:**
> borra todo lo que hiciste en este PC, tenemos que hacerlo desde la EC2 (conexión: `ssh -i "buildcorp.pem" ubuntu@100.60.151.204`)

**Apoyo de la IA:**
- Revirtió en GitHub el commit con el script SSL y los cambios de README/PLANIFICACION/settings (`git revert`), conservando solo este registro.
- Por SSH en la EC2 (Ubuntu 26.04, Python 3.14, PostgreSQL 18, Nginx 1.28): actualizó el sistema, clonó el repo y ejecutó `deploy/setup_ec2.sh` (PostgreSQL, migraciones, estáticos, datos demo, Gunicorn con systemd, Nginx como proxy inverso y cron).
- Configuró HTTPS en el servidor: certificado Let's Encrypt para `100-60-151-204.sslip.io` (certbot por webroot, renovación automática con `certbot.timer`), bloque Nginx 443 con TLS 1.2/1.3 y HSTS, redirección del dominio a HTTPS y acceso por IP en HTTP intacto; actualizó `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `SITE_URL` en el `.env` del servidor.
- Verificó: servicios activos, 34 activos en PostgreSQL, admin con estilos y login con CSRF correcto por `http://100.60.151.204` y por `https://100-60-151-204.sslip.io`.

**Archivos:** `prompts_ia.md` (modificado). En la EC2: `/etc/nginx/sites-available/buildcorp`, `/etc/nginx/snippets/buildcorp_app.conf`, `.env` (configuración del servidor)

---

### #24 · 2026-11-11 · Botón de ayuda con credenciales de prueba en el login

**Prompt:**
> quiero que coloques un signo de interrogacion en la pagina del login para colocar las credenciales y no tener que acordarme, que sirva para pruebas

**Apoyo de la IA:**
- Agregó un botón «?» junto al título del login que despliega los usuarios demo (admin, bodeguero, encargado, ventas) y la contraseña de la demo; al hacer clic en un usuario se rellena el formulario.
- Lo dejó controlado por la variable `MOSTRAR_CREDENCIALES_DEMO` (activa por defecto; `False` en el `.env` lo oculta), expuesta a las plantillas mediante el context processor de usuarios.

**Archivos:** `templates/registration/login.html`, `static/css/buildcorp.css`, `buildcorp/settings/base.py`, `apps/usuarios/context_processors.py`, `.env.example` (modificados), `prompts_ia.md` (modificado)

---

### #25 · 2026-11-11 · Subir el botón de credenciales a la EC2

**Prompt:**
> hacelo

**Apoyo de la IA:**
- Hizo commit y push del botón «?» del login (sin incluir apuntes locales que había en `.env.example`).
- En la EC2: `git pull`, `collectstatic` y reinicio de Gunicorn; verificó que el login publicado muestra el botón.

**Archivos:** `prompts_ia.md` (modificado). En la EC2: actualización del código desplegado

---

### #26 · 2026-11-11 · ¿Se puede desplegar automáticamente?

**Prompt:**
> siempre tengo que meterme al servidor para incorporar los cambios?, no puede ser automatico

**Apoyo de la IA:**
- Explicó dos formas de automatizar el despliegue: GitHub Actions que entra por SSH al hacer push, o una tarea programada en la EC2 que revisa GitHub cada pocos minutos y se actualiza sola.
- Recomendó la segunda para AWS Academy (la IP cambia al reiniciar el laboratorio y no requiere guardar la llave `.pem` en GitHub ni abrir el puerto 22 a internet).

**Archivos:** `prompts_ia.md` (modificado)

---

### #27 · 2026-11-11 · Despliegue automático en la EC2

**Prompt:**
> haz lo que haga falta

**Apoyo de la IA:**
- Creó `deploy/actualizar.sh`: si `origin/main` tiene commits nuevos hace `git merge --ff-only`, instala dependencias si cambió `requirements.txt`, aplica `migrate` y `collectstatic` y reinicia Gunicorn; usa un lock para no solaparse y registra cada despliegue en `/home/ubuntu/buildcorp-deploy.log`.
- Creó el servicio y el timer de systemd (`buildcorp-actualizar`) que lo ejecutan cada 2 minutos, y los agregó a `setup_ec2.sh` para futuras instalaciones.
- Documentó el flujo en el README y la decisión en PLANIFICACION; activó el timer en la EC2 (instalación manual única) y lo probó subiendo un segundo commit sin entrar al servidor, que se desplegó solo.

**Archivos:** `deploy/actualizar.sh`, `deploy/buildcorp-actualizar.service`, `deploy/buildcorp-actualizar.timer` (creados), `deploy/setup_ec2.sh`, `README.md`, `PLANIFICACION.md`, `prompts_ia.md` (modificados)

---

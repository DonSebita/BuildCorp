# Graph Report - BuildCorp  (2026-11-05)

## Corpus Check
- Corpus is ~34,996 words - fits in a single context window. You may not need a graph.

## Summary
- 912 nodes · 1921 edges · 90 communities (43 shown, 47 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 289 edges (avg confidence: 0.92)
- Token cost: 325,939 input · 0 output

## Community Hubs (Navigation)
- API de préstamos y validación
- Plantillas de activos y API
- Cobros y reglas de arriendo
- Vistas del dashboard y permisos
- API de mantenimiento
- Servicios del dashboard
- Configuración de apps Django
- Servicios de préstamos (cálculo)
- Migraciones iniciales
- Admin de préstamos y firmas
- Vistas y formularios de activos
- Admin de activos
- Alertas y solicitud de baja
- Bandeja de alertas y QR
- Formularios de activos y mantención
- Modelo de datos (planificación)
- API de bodegas y categorías
- Modelo Activo y vistas de ficha
- API y servicios de alertas
- Conceptos de terreno y estados
- Inlines del admin
- Modelos de bodega y paquetes
- Vistas de contratistas
- Datos demo y pruebas
- Sistema visual Talonario
- Vistas de entrega y devolución
- Comando cargar_demo
- Roles y morosidad
- Identificación QR y stack
- Usuarios y roles
- ViewSet de activos
- Parámetros del sistema
- Disponibilidad de paquetes
- Modelo y servicio de mantención
- Pruebas de cálculo y flujo
- Paquetes de maquinaria
- Comandos de morosidad y roles
- Modelo Contratista
- Despliegue EC2 y cron
- API de contratistas y obras
- Admin de mantenimiento
- Cliente JS api.js
- Admin de catálogos
- Generación de QR
- Listas de bodegas y paquetes
- Admin de contratistas
- Creación de contratistas y obras
- Detalle de préstamo
- Dashboard y API REST
- Revisión diaria de mantenciones
- Migraciones de usuarios
- Registrar mantención
- Login de usuarios
- Admin de alertas
- ViewSet de alertas
- ViewSet de contratistas
- Lista de cobros
- Paginación DRF
- Lista de mantenimientos
- Firma en canvas (JS)
- Hoja y tablas responsive
- Marca y favicon
- Estructura del repositorio
- Pantallas del frontend

## God Nodes (most connected - your core abstractions)
1. `Activo` - 52 edges
2. `RolRequeridoMixin` - 42 edges
3. `Prestamo` - 33 edges
4. `Alerta` - 32 edges
5. `Contratista` - 32 edges
6. `PlanMantenimiento` - 28 edges
7. `Command` - 28 edges
8. `PaqueteMaquinaria` - 23 edges
9. `Mantenimiento` - 22 edges
10. `Cobro` - 22 edges

## Surprising Connections (you probably didn't know these)
- `Cliente JS BC (static/js/api.js: api, clp, esc, aviso, ocupado, timbre)` --semantically_similar_to--> `Template tag {% timbre %} (sello de estado)`  [INFERRED] [semantically similar]
  templates/base.html → apps/prestamos/templates/prestamos/cobro.html
- `activos/escanear.html (Escanear QR)` --calls--> `montar()`  [EXTRACTED]
  apps/activos/templates/activos/escanear.html → static/js/escaner.js
- `mantenimiento/registrar.html (Registrar mantención)` --calls--> `montar()`  [EXTRACTED]
  apps/mantenimiento/templates/mantenimiento/registrar.html → static/js/escaner.js
- `Direction contract (folio rojo + estado timbrado)` --implements--> `Sistema visual Talonario de arriendo`  [INFERRED]
  .impeccable/surfaces/templates-base-html.md → DESIGN.md
- `Cron 06:00 revisar_morosidad` --calls--> `manage.py revisar_morosidad`  [INFERRED]
  deploy/crontab.txt → PLANIFICACION.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Ciclo de arriendo: entrega firmada, devolucion, cobro CLP y paso a mantencion** — planificacion_flujo_entrega, planificacion_flujo_devolucion, planificacion_firma, planificacion_reglas_cobro_clp, planificacion_mantenimiento_preventivo, planificacion_prestamo [EXTRACTED 0.95]
- **Tareas diarias por cron (morosidad y mantenciones)** — deploy_crontab_revisar_morosidad_job, deploy_crontab_revisar_mantenimientos_job, planificacion_revisar_morosidad, planificacion_revisar_mantenimientos, planificacion_alerta [INFERRED 0.85]
- **Componentes del lenguaje visual Talonario de arriendo** — design_talonario_de_arriendo, design_folio, design_timbre, design_copia_rol, design_kpis, design_riel, _impeccable_surfaces_templates_base_html_direction_contract [EXTRACTED 0.95]
- **Flujo QR: etiqueta, escaneo y registro de mantención** — apps_activos_templates_activos_etiquetas, url_activos_qr, apps_activos_templates_activos_escanear, static_js_escaner_montar, apps_mantenimiento_templates_mantenimiento_registrar [INFERRED 0.85]
- **Vistas del plan de mantención preventiva** — apps_activos_templates_activos_ficha, apps_mantenimiento_templates_mantenimiento_lista, apps_mantenimiento_templates_mantenimiento_fila_plan, apps_mantenimiento_templates_mantenimiento_registrar, plan_mantencion_preventiva [INFERRED 0.85]
- **Plantillas que renderizan en cliente vía BC.api y la API REST** — apps_activos_templates_activos_lista, apps_alertas_templates_alertas_bandeja, apps_activos_templates_activos_escanear, apps_activos_templates_activos_ficha, static_js_api [INFERRED 0.85]
- **Flujo de entrega de préstamo (nuevo, detalle, entregar con firma, comprobante)** — apps_prestamos_templates_prestamos_nuevo_template, apps_prestamos_templates_prestamos_detalle_template, apps_prestamos_templates_prestamos_entregar_template, templates_includes_firma_template, apps_prestamos_templates_prestamos_comprobante_template [INFERRED 0.85]
- **Flujo de devolución y cobro (devolver, cobro automático, pago)** — apps_prestamos_templates_prestamos_devolver_template, apps_prestamos_templates_prestamos_devolver_api_devolver, apps_prestamos_templates_prestamos_cobros_template, apps_prestamos_templates_prestamos_cobro_template, apps_prestamos_templates_prestamos_cobro_registrar_pago [INFERRED 0.85]
- **Endpoints REST de préstamos consumidos desde plantillas** — apps_prestamos_templates_prestamos_lista_api_prestamos, apps_prestamos_templates_prestamos_nuevo_api_cotizar, apps_prestamos_templates_prestamos_entregar_api_entregar, apps_prestamos_templates_prestamos_entregar_api_asignar_activos, apps_prestamos_templates_prestamos_entregar_api_quitar_activo, apps_prestamos_templates_prestamos_devolver_api_devolver [EXTRACTED 1.00]

## Communities (90 total, 47 thin omitted)

### Community 0 - "API de préstamos y validación"
Cohesion: 0.06
Nodes (34): como_drf(), validar_entregable(), CobroViewSet, ip_de(), PrestamoFilter, Meta, PrestamoViewSet, Firma (+26 more)

### Community 1 - "Plantillas de activos y API"
Cohesion: 0.09
Nodes (37): api-dashboard-resumen endpoint, API GET /api/v1/activos/, API POST /api/v1/activos/<id>/cambiar-estado/, API GET /api/v1/activos/codigo/<codigo>/, API POST /api/v1/activos/<id>/trasladar/, API /api/v1/alertas/ (listar, marcar-leida, resolver), activos/bodegas.html (Bodegas e inventario), activos/escanear.html (Escanear QR) (+29 more)

### Community 2 - "Cobros y reglas de arriendo"
Cohesion: 0.09
Nodes (35): Filtro de plantilla |clp (formato pesos chilenos), Recargo por atraso (días x tarifa diaria x params.recargo_atraso), Acción Registrar pago (prestamos:pagar, cierra préstamo), Template cobro.html (detalle de cobro), Template tag {% timbre %} (sello de estado), Exportar CSV (dashboard:exportar), Template cobros.html (lista de cobros), Template comprobante.html (comprobante imprimible) (+27 more)

### Community 3 - "Vistas del dashboard y permisos"
Cohesion: 0.09
Nodes (9): ExportarCSVView, InicioView, PermisoPorRol, roles_para(), tiene_rol(), clp(), miles(), puede() (+1 more)

### Community 4 - "API de mantenimiento"
Cohesion: 0.13
Nodes (6): MantenimientoViewSet, PlanViewSet, PlanMantenimiento, Meta, PlanSerializer, Meta

### Community 5 - "Servicios del dashboard"
Cohesion: 0.12
Nodes (14): HistorialEstado, Meta, ResumenView, cobros_pendientes(), fila_prestamo(), grafico_estados(), grafico_facturacion(), kpi() (+6 more)

### Community 6 - "Configuración de apps Django"
Cohesion: 0.09
Nodes (7): ActivosConfig, AlertasConfig, ContratistasConfig, DashboardConfig, MantenimientoConfig, PrestamosConfig, UsuariosConfig

### Community 7 - "Servicios de préstamos (cálculo)"
Cohesion: 0.15
Nodes (10): revisar_plan(), calcular_arriendo(), calcular_totales(), cotizar(), desglose(), devolver(), dias_entre(), generar_cobro() (+2 more)

### Community 8 - "Migraciones iniciales"
Cohesion: 0.14
Nodes (8): Migration, Migration, Migration, Migration, Migration, Migration, Migration, Migration

### Community 9 - "Admin de préstamos y firmas"
Cohesion: 0.13
Nodes (7): CobroAdmin, DetalleInline, FirmaAdmin, FirmaInline, PaqueteInline, ParametroAdmin, PrestamoAdmin

### Community 10 - "Vistas y formularios de activos"
Cohesion: 0.15
Nodes (7): ActivoForm, Meta, CrearView, EditarView, PaqueteCrearView, PaqueteEditarView, PaqueteFormMixin

### Community 11 - "Admin de activos"
Cohesion: 0.16
Nodes (5): ActivoAdmin, cambiar_estado(), crear_activo(), dar_de_baja(), enviar_a_mantenimiento()

### Community 12 - "Alertas y solicitud de baja"
Cohesion: 0.18
Nodes (10): SolicitarBajaView, Alerta, Meta, Nivel, Tipo, crear_alerta(), resolver_alertas(), bloquear() (+2 more)

### Community 13 - "Bandeja de alertas y QR"
Cohesion: 0.12
Nodes (5): QRView, BandejaView, ListaView, PagarView, RolRequeridoMixin

### Community 14 - "Formularios de activos y mantención"
Cohesion: 0.18
Nodes (8): ItemForm, Meta, PaqueteForm, Meta, TrasladoForm, MantenimientoForm, Meta, EstiloMixin

### Community 15 - "Modelo de datos (planificación)"
Cohesion: 0.16
Nodes (15): Cron 06:10 revisar_mantenimientos, Entidad Activo, Entidad CategoriaActivo, Entidad Cobro, Entidad Contratista (ACTIVO / BLOQUEADO), Entidad Firma (hash SHA-256, IP, fecha), Flujo de entrega (prestamo), Modelo de datos (+7 more)

### Community 16 - "API de bodegas y categorías"
Cohesion: 0.17
Nodes (10): ActivoFilter, Meta, BodegaViewSet, CategoriaViewSet, CategoriaActivo, Meta, ActivoSerializer, Meta (+2 more)

### Community 17 - "Modelo Activo y vistas de ficha"
Cohesion: 0.14
Nodes (8): Activo, Estado, Meta, EscanearView, EtiquetasView, FichaView, linea_de_estados(), ListaView

### Community 18 - "API y servicios de alertas"
Cohesion: 0.20
Nodes (5): AlertaSerializer, Meta, alertas_para(), rol(), rol_de()

### Community 19 - "Conceptos de terreno y estados"
Cohesion: 0.14
Nodes (15): Linea de estados (barra de 180 dias), Pantallas de terreno (pasos, botones 44px, canvas de firma), Timbre (badge de estado, {% timbre %} / BC.timbre), Checklist de entrega, Django Admin personalizado, Flujo de devolucion, Hoja de vida del equipo (HistorialEstado), Mantenimiento preventivo (usos, horas, dias: gana el primero) (+7 more)

### Community 20 - "Inlines del admin"
Cohesion: 0.20
Nodes (6): exportar_csv(), HistorialInline, ItemInline, MantenimientoInline, PlanInline, ObraInline

### Community 21 - "Modelos de bodega y paquetes"
Cohesion: 0.18
Nodes (11): Bodega, Meta, Tipo, ItemPaquete, Meta, Traslado, Meta, BodegaSerializer (+3 more)

### Community 22 - "Vistas de contratistas"
Cohesion: 0.16
Nodes (5): BloqueoView, EditarView, ObraEditarView, ObraForm, Meta

### Community 24 - "Sistema visual Talonario"
Cohesion: 0.19
Nodes (12): Superficie: app interna BuildCorp (shell + dashboards por rol), static/css/buildcorp.css (fuente de verdad), Franja de copia por rol (.copia-rol), Sistema visual Talonario de arriendo, Tipografia Archivo (wdth/wght variables, cifras tabulares), Tokens de diseno (--tinta, --papel, --folio, estados), Dashboard por rol, Plan de trabajo por fases (0-10) (+4 more)

### Community 25 - "Vistas de entrega y devolución"
Cohesion: 0.22
Nodes (6): CobroView, ComprobanteView, DetalleView, DevolverView, EntregarView, PrestamoMixin

### Community 27 - "Roles y morosidad"
Cohesion: 0.18
Nodes (12): Contexto del proyecto (software interno, 4 roles), Contexto y objetivo (sistema interno de alquiler), Morosidad y bloqueo automatico (DIAS_GRACIA), RF4 Alertas de morosidad y bloqueo automatico, Rol Administrador, Rol Bodeguero, Rol Encargado de entrega/recepcion, Rol Ventas (+4 more)

### Community 28 - "Identificación QR y stack"
Cohesion: 0.15
Nodes (14): Folio (.folio) codigos en rojo, Escaneo QR (html5-qrcode, modo tomar foto sin HTTPS), Folio de mantencion MNT-AAAA-NNNN, Identificacion unica de cada maquina (codigo interno + QR), Entidad Mantenimiento, Stack tecnologico, Entrada #6: cambio de SQLite a PostgreSQL (select_for_update of self), Django==6.0.10 (+6 more)

### Community 29 - "Usuarios y roles"
Cohesion: 0.15
Nodes (3): UsuarioAdmin, Usuario, Meta

### Community 30 - "ViewSet de activos"
Cohesion: 0.24
Nodes (8): ActivoViewSet, HistorialSerializer, Meta, TrasladoSerializer, Meta, trasladar(), MantenimientoSerializer, Meta

### Community 31 - "Parámetros del sistema"
Cohesion: 0.17
Nodes (5): ParametroSistema, Meta, ParametrosForm, Meta, ParametrosView

### Community 32 - "Disponibilidad de paquetes"
Cohesion: 0.24
Nodes (4): disponibilidad_paquete(), disponibles_por_categoria(), ListaView, NuevoView

### Community 33 - "Modelo y servicio de mantención"
Cohesion: 0.26
Nodes (7): Mantenimiento, Estado, Meta, Tipo, finalizar(), registrar_mantenimiento(), siguiente_folio()

### Community 34 - "Pruebas de cálculo y flujo"
Cohesion: 0.20
Nodes (3): CalculoCLPTests, firma(), FlujoArriendoTests

### Community 35 - "Paquetes de maquinaria"
Cohesion: 0.20
Nodes (5): PaqueteViewSet, PaqueteMaquinaria, Meta, PaqueteSerializer, Meta

### Community 36 - "Comandos de morosidad y roles"
Cohesion: 0.20
Nodes (3): Command, revisar_morosidad(), Command

### Community 37 - "Modelo Contratista"
Cohesion: 0.18
Nodes (6): Contratista, Estado, Meta, ContratistaForm, Meta, DetalleView

### Community 38 - "Despliegue EC2 y cron"
Cohesion: 0.20
Nodes (10): Cron 06:00 revisar_morosidad, DJANGO_SETTINGS_MODULE, setup_ec2.sh script, Entidad Alerta (GenericForeignKey, rol_destino), Arquitectura (Nginx -> Gunicorn -> Django/DRF -> PostgreSQL + cron), manage.py cargar_demo (datos semilla), Despliegue en AWS EC2 (AWS Academy), manage.py revisar_morosidad (+2 more)

### Community 39 - "API de contratistas y obras"
Cohesion: 0.33
Nodes (7): ObraViewSet, Obra, Meta, ContratistaSerializer, Meta, ObraSerializer, Meta

### Community 40 - "Admin de mantenimiento"
Cohesion: 0.28
Nodes (3): badge(), MantenimientoAdmin, PlanAdmin

### Community 42 - "Cliente JS api.js"
Cohesion: 0.28
Nodes (3): api(), cookie(), mensajeDeError()

### Community 43 - "Admin de catálogos"
Cohesion: 0.25
Nodes (5): BodegaAdmin, CategoriaAdmin, HistorialAdmin, PaqueteAdmin, TrasladoAdmin

### Community 48 - "Detalle de préstamo"
Cohesion: 0.29
Nodes (5): DetallePrestamo, EstadoFisico, Meta, DetalleSerializer, Meta

### Community 49 - "Dashboard y API REST"
Cohesion: 0.33
Nodes (6): First viewport: riel 232px, franja de rol, 4 KPIs, tabla + bandeja de alertas, KPIs (.kpis) con filetes, critica en rojo folio, Riel de navegacion (offcanvas < 992px), API REST DRF /api/v1/, GET /api/v1/dashboard/resumen/, django-filter==26.2

## Knowledge Gaps
- **43 isolated node(s):** `DJANGO_SETTINGS_MODULE`, `static/css/buildcorp.css (fuente de verdad)`, `Tipografia Archivo (wdth/wght variables, cifras tabulares)`, `Riel de navegacion (offcanvas < 992px)`, `Hoja (.hoja) contenedor de tablas y formularios` (+38 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 335 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **47 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Activo` connect `Modelo Activo y vistas de ficha` to `API de préstamos y validación`, `Vistas del dashboard y permisos`, `Servicios del dashboard`, `Servicios de préstamos (cálculo)`, `Vistas y formularios de activos`, `Admin de activos`, `Alertas y solicitud de baja`, `Bandeja de alertas y QR`, `Formularios de activos y mantención`, `API de bodegas y categorías`, `Inlines del admin`, `Modelos de bodega y paquetes`, `Datos demo y pruebas`, `Comando cargar_demo`, `ViewSet de activos`, `Disponibilidad de paquetes`, `Modelo y servicio de mantención`, `Pruebas de cálculo y flujo`, `Generación de QR`, `Listas de bodegas y paquetes`, `Revisión diaria de mantenciones`, `Registrar mantención`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 32 inferred relationships involving `Activo` (e.g. with `ActivoFilter` and `ActivoViewSet`) actually correct?**
  _`Activo` has 32 INFERRED edges - model-reasoned connections that need verification._
- **What connects `DJANGO_SETTINGS_MODULE`, `static/css/buildcorp.css (fuente de verdad)`, `Tipografia Archivo (wdth/wght variables, cifras tabulares)` to the rest of the system?**
  _43 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `API de préstamos y validación` be split into smaller, more focused modules?**
  _Cohesion score 0.06101190476190476 - nodes in this community are weakly interconnected._
- **Why does `RolRequeridoMixin` connect `Bandeja de alertas y QR` to `Disponibilidad de paquetes`, `Vistas del dashboard y permisos`, `Modelo Contratista`, `Vistas y formularios de activos`, `Alertas y solicitud de baja`, `Listas de bodegas y paquetes`, `Formularios de activos y mantención`, `Creación de contratistas y obras`, `Modelo Activo y vistas de ficha`, `Vistas de contratistas`, `Registrar mantención`, `Vistas de entrega y devolución`, `Lista de cobros`, `Lista de mantenimientos`, `Parámetros del sistema`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `Prestamo` (e.g. with `resumen()` and `PrestamoFilter`) actually correct?**
  _`Prestamo` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Should `Plantillas de activos y API` be split into smaller, more focused modules?**
  _Cohesion score 0.09090909090909091 - nodes in this community are weakly interconnected._
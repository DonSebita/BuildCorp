# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Fijado por la rúbrica y PLANIFICACION.md: Django 5 + Django REST Framework, PostgreSQL, Django Templates con Bootstrap 5, JS vanilla (fetch) y Chart.js. Despliegue en una sola EC2 de AWS Academy (Nginx + Gunicorn + cron).

## Users

Personal interno de BuildCorp, una empresa chilena de arriendo de herramientas y maquinaria ligera. Cuatro roles:

- **Administrador**: control total, parámetros, desbloqueos, bajas, reportes.
- **Bodeguero**: custodia física del inventario, traslados entre bodegas y mantenciones. Trabaja en bodega, a menudo con el celular en la mano frente a la máquina.
- **Encargado de entrega/recepción**: revisa equipos al salir y volver, registra horómetro, daños y la firma del responsable de obra. Trabaja en terreno, en tablet o celular.
- **Ventas**: contratistas, obras, solicitudes de arriendo, paquetes, cobros y morosidad. Trabaja en escritorio.

Los contratistas y subcontratistas no tienen cuenta; solo firman en el dispositivo del encargado.

## Product Purpose

Centralizar préstamos, trazabilidad entre bodegas de obra, hojas de vida de equipos y mantenimiento preventivo, para reducir pérdidas de maquinaria, cobros inexactos y fallas imprevistas. Éxito: cada máquina tiene un estado y una ubicación verificables en todo momento, y cada arriendo termina en un cobro correcto en CLP.

## Positioning

Software interno, no tienda en línea. La separación de funciones (Ventas crea, el Encargado entrega y recibe) y el ciclo de estados auditado por activo son el núcleo.

## Operating Context

- Cada máquina tiene un código inmutable (`RTM-0004`) y una etiqueta QR que se escanea en entrega, devolución y mantención.
- La firma del responsable de obra se captura en un canvas, en terreno.
- Tareas diarias por cron: revisión de morosidad (bloqueo automático tras días de gracia) y de mantenciones.
- Moneda CLP sin decimales, configuración regional `es-cl`, zona `America/Santiago`.

## Capabilities and Constraints

- Estados de activo: Disponible, En Uso, Mantenimiento, Dado de Baja. Los cambios ocurren solo en la capa de servicios y quedan en el historial.
- Paquetes de maquinaria definidos por categoría y cantidad.
- Mantención preventiva por usos, horas de horómetro o días (gana el primero).
- Días de gracia por defecto: 3. Comprobante: vista HTML imprimible (sin PDF generado en servidor).
- Correo electrónico opcional; las alertas viven en el sistema.

## Brand Commitments

No hay logo ni paleta definidos; la identidad visual se propone en el proyecto. El usuario pidió un diseño empresarial y fácil de usar, con dashboards distintos según el rol.

## Evidence on Hand

Solo datos de demostración (comando `cargar_demo`). Las tarifas de paquetes son referenciales. No inventar clientes reales, cifras de negocio ni testimonios.

## Product Principles

1. Cada pantalla responde primero "¿qué tengo que hacer hoy?" para el rol que la mira.
2. El estado de una máquina debe leerse de un vistazo y de forma consistente en toda la app.
3. Las pantallas de terreno (entrega, devolución, mantención) se piensan primero para tablet y celular.
4. Ninguna acción irreversible sin confirmación ni rastro de quién la hizo.

## Accessibility & Inclusion

Uso en exteriores y con guantes en terreno: objetivos táctiles grandes y contraste alto. El estado nunca se comunica solo con color.

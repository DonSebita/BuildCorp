---
version: 1
slug: "templates-base-html"
primary_target: "templates/base.html"
related_targets: ["apps/dashboard/templates/dashboard/inicio.html"]
---

# Superficie: app interna BuildCorp (shell + dashboards por rol)

Modo: Operate. Audiencia: personal interno (Admin, Bodeguero, Encargado E/R, Ventas). Tarea: ver qué toca hoy según el rol y operar préstamos, activos, mantenciones y cobros. Pantallas de terreno pensadas para tablet/celular.

## Direction contract

THESIS: Cada registro es un folio de talonario: número rojo, estado timbrado, nada se borra, se anula. Rechaza el panel Bootstrap genérico de tarjetas blancas con un acento azul.

OWN-WORLD: Riel lateral en tinta carbón violeta (#2E2A6E), fondo papel frío, folios en rojo talonario, cada rol con su franja de copia (amarilla Ventas, rosada Bodega, celeste Terreno, blanca Admin). Badges de estado como timbres con borde, misma forma a todo tamaño. Archivo con anchos variables; cifras tabulares.

STORY: El usuario entra, ve su franja de rol, sus 4 cifras clave y la lista de lo que vence o requiere acción; actúa con un botón primario.

FIRST VIEWPORT: Riel izquierdo 232px; franja de rol con saludo y acción primaria a la derecha; fila de 4 KPIs grandes con filete izquierdo (el crítico en rojo); debajo tabla principal (2/3) y bandeja de alertas (1/3).

FORM: Talonario de arriendo autocopiativo, candidato 3 de 7. seed:28ae25dffa65acc1. Signature move: folio rojo + estado timbrado; hoja de vida con estados sobre una misma línea base.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

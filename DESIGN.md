# DESIGN · BuildCorp «Talonario de arriendo»

Sistema visual de la app interna (modo Operate). Fuente de verdad del código: `static/css/buildcorp.css`.

## Idea

Cada registro es un folio de talonario autocopiativo: número rojo, estado timbrado, nada se borra (se anula). Cada rol trabaja en su "copia" de color.

## Tokens

| Token | Valor | Uso |
|---|---|---|
| `--tinta` | `#2e2a6e` | Riel de navegación, botón primario, foco, serie "En uso" |
| `--papel` | `#f3f3f7` | Fondo de página |
| `--superficie` | `#ffffff` | Hojas (paneles) |
| `--linea` / `--linea-suave` | `#dddbe8` / `#ecebf2` | Bordes y separadores |
| `--texto` / `--texto-2` | `#1d1b3a` / `#57547a` | Texto principal / secundario |
| `--folio` | `#c8102e` | Folios y códigos, KPI crítico |
| `--ok` `--warn` `--crit` | `#2d6a3e` `#7f5a00` `#c8102e` | Estados (con fondos `-fondo`) |
| Copia Ventas | `#f4e4a1` | Franja del dashboard y ítem activo del riel |
| Copia Bodega | `#f6d9df` | idem |
| Copia Terreno (Encargado E/R) | `#d5e5f2` | idem |
| Copia Admin | `#ffffff` | idem |

Tipografía: **Archivo** (Google Fonts, ejes `wdth` 62–125 y `wght` 400–800). Cifras KPI a `font-stretch: 78%`, peso 800; cabeceras de tabla en mayúsculas a 90 % de ancho; números siempre tabulares. Radio de hojas 10 px; elevación solo con borde de 1 px (sin sombras salvo los avisos flotantes).

## Componentes

- **Riel**: tinta, 236 px; en < 992 px pasa a offcanvas con barra superior (menú, escanear, alertas).
- **Franja de copia** (`.copia-rol`): saludo, rol timbrado, fecha y acciones primarias del rol.
- **KPIs** (`.kpis`): cuatro cifras grandes separadas por filetes, sin tarjetas; la crítica en rojo folio con "requiere acción".
- **Hoja** (`.hoja`, `.hoja-cabeza`, `.hoja-cuerpo`): contenedor único de tablas y formularios.
- **Timbre** (`{% timbre %}`, `BC.timbre`): badge con borde de 1,5 px, siempre con texto. Dado de baja va tachado. Animación `timbre-nuevo` solo al cambiar un estado.
- **Folio** (`.folio`): códigos `P-2026-0001`, `RTM-0004`, `MNT-2026-0001` en rojo.
- **Línea de estados**: barra de 180 días con los tramos de estado del activo a una misma escala.
- **Tablas**: en < 576 px se apilan como fichas (etiqueta a la izquierda, valor a la derecha, acción arriba a la derecha).
- **Pantallas de terreno**: pasos numerados, opciones de estado como botones de 44 px, horómetro con sufijo "h", canvas de firma con línea guía.

## Reglas

- El estado nunca se comunica solo con color.
- Objetivos táctiles ≥ 44 px (56 px en acciones principales de terreno).
- Una sola animación propia (timbrar); `prefers-reduced-motion` la desactiva.
- Impresión: comprobantes y etiquetas ocultan riel y controles.

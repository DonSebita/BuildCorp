# Instrucciones para la IA en este proyecto

## Registro obligatorio en `prompts_ia.md`

La rúbrica exige un registro del uso de IA. **En cada mensaje del usuario**, antes de terminar la respuesta, agrega una entrada nueva al final de la sección "Registro" de [prompts_ia.md](prompts_ia.md) con este formato:

```markdown
### #<n> · <AAAA-MM-DD> · <título corto>

**Prompt:**
> <texto del usuario, textual o resumido si es muy largo; omite datos sensibles como claves o contraseñas>

**Apoyo de la IA:**
- <qué hizo o explicó la IA, en viñetas breves>

**Archivos:** `<archivo>` (creado/modificado), ... o "Ninguno (solo consulta)"

---
```

- Numera las entradas de forma correlativa.
- Registra también las consultas que no modifican archivos (dudas, explicaciones, errores).
- No borres ni reescribas entradas anteriores.

## Contexto del proyecto

- La guía del proyecto está en [PLANIFICACION.md](PLANIFICACION.md). Si cambia una decisión, actualiza también ese archivo.
- Es un software **interno** de BuildCorp (Django + DRF + PostgreSQL, desplegado en una EC2 de AWS Academy). Los clientes no inician sesión.
- Roles: Administrador, Bodeguero, Encargado de entrega/recepción y Ventas.
- Responde en español.

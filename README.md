# White Bear Restaurant — Reservaciones

Sitio de reservaciones online para White Bear Restaurant (2793 Wilmington Rd,
Lake Placid, NY), con un panel en tiempo real pensado para mostrarse en una
tablet del restaurante.

## Qué incluye

- **`public/index.html`** — página para que los clientes reserven mesa (nombre,
  teléfono, fecha, hora, número de personas, ocasión y notas).
- **`public/tablet.html`** — panel para el staff, optimizado para tablet:
  se actualiza solo cada 5 segundos, agrupa por Hoy / Próximas / Todas,
  filtra por estado (pendiente, confirmada, etc.) y permite avanzar cada
  reservación con botones grandes: Confirmar → Sentar → Finalizar, o Cancelar.
- **`server.py`** — backend en Python (sin dependencias externas) que valida
  las reservaciones (horario del restaurante, tamaño de grupo, fecha no
  pasada) y las guarda en `data/reservations.json`. Como cliente y tablet
  hablan con el mismo servidor, cualquier reservación nueva aparece en la
  tablet automáticamente, sin recargar la página.

## Cómo ejecutarlo

Requiere solo Python 3 (viene preinstalado en Mac/Linux).

```bash
python3 server.py 8000
```

Luego abre:

- Sitio de clientes: http://localhost:8000/
- Panel para tablet: http://localhost:8000/tablet.html

En la tablet del restaurante, abre esa misma URL usando la IP de la
computadora que corre el servidor en tu red local (por ejemplo
`http://192.168.1.50:8000/tablet.html`) en vez de `localhost`.

## Horario y reglas configuradas

- Lunes a jueves y domingo: 11:00 a.m. – 9:00 p.m. Viernes y sábado: 11:00
  a.m. – 9:30 p.m. (la hora exacta de cierre varía por día; la última hora
  para reservar es 30 minutos antes de cerrar).
- Grupos de 1 a 40 personas (para grupos más grandes se sugiere llamar).
- No se permiten fechas pasadas.

Estos valores están en el diccionario `RESTAURANT` al inicio de `server.py`.

## Menú de preorden para grupos grandes

A partir de 20 personas, el formulario de reservación muestra automáticamente
un menú reducido para que el grupo preordene, y el pedido aparece en la
tarjeta de la tablet (sección "🍽️ Preorden"). Los platillos son un
**placeholder** por ahora — para poner el menú real, edita la lista
`RESTAURANT["groupMenu"]["items"]` en `server.py`:

```python
"items": [
    {"id": "item-1", "name": "Nombre del platillo", "description": "Opcional"},
    ...
],
```

No hace falta tocar el HTML/JS: el formulario y la tablet leen esta lista
desde el servidor. El umbral de 20 personas y la nota introductoria también
se pueden ajustar ahí (`"threshold"` y `"note"`).

## Siguientes pasos sugeridos

- Poner esto en un servidor real (o Hostinger) para que sea accesible desde
  internet y no solo en la red local.
- Añadir notificación por correo/SMS al restaurante cuando llega una
  reservación nueva.
- Agregar login para el panel de tablet si se va a exponer públicamente.

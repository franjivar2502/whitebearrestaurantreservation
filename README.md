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

## Publicarlo en internet (link público, gratis)

El proyecto ya está listo para desplegarse en **Render.com** (plan gratis,
sin tarjeta). Ya tiene: un repositorio Git inicializado con un primer commit,
y el servidor lee el puerto desde la variable de entorno `PORT` (lo que pide
Render).

1. **Sube el código a GitHub** (si no tienes cuenta, créala gratis en
   github.com):
   - Crea un repositorio nuevo y vacío en GitHub (sin README, sin licencia).
   - En la terminal, dentro de esta carpeta:
     ```bash
     git remote add origin https://github.com/TU-USUARIO/white-bear-reservations.git
     git branch -M main
     git push -u origin main
     ```
2. **Crea una cuenta gratis en [render.com](https://render.com)** (no pide
   tarjeta para el plan gratuito).
3. **New +** → **Web Service** → conecta tu cuenta de GitHub → elige el
   repositorio que acabas de subir.
4. Configuración del servicio:
   - **Runtime:** Python 3
   - **Build Command:** (déjalo vacío, no hay dependencias que instalar)
   - **Start Command:** `python3 server.py`
   - **Instance Type:** Free
5. **Create Web Service**. En unos minutos Render te da un link público tipo
   `https://white-bear-reservations.onrender.com` — ese es el que puedes
   compartir y abrir desde cualquier celular, en cualquier red.

### Limitaciones del plan gratis de Render (a tener en cuenta)

- El servicio "se duerme" tras ~15 minutos sin visitas; la primera visita
  después de eso tarda ~30-50 segundos en responder mientras despierta.
- El archivo `data/reservations.json` **no es permanente** en el plan
  gratis: si el servicio se reinicia (se duerme y despierta, o hay un nuevo
  despliegue), las reservaciones guardadas se pierden. Es aceptable para
  probar el sitio, pero **antes de usarlo en producción con clientes
  reales conviene mover el almacenamiento a algo persistente** (un disco
  persistente de Render, ~$7/mes, o una base de datos). Avísame cuando
  llegue ese momento y lo dejamos resuelto.

## Otros siguientes pasos sugeridos

- Añadir notificación por correo/SMS al restaurante cuando llega una
  reservación nueva.
- Agregar login para el panel de tablet si se va a exponer públicamente.
- Resolver el almacenamiento persistente (ver arriba) antes de usarlo en
  producción.

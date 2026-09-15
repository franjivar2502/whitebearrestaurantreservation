# White Bear Restaurant — Reservaciones

Sitio de reservaciones online para White Bear Restaurant (2793 Wilmington Rd,
Lake Placid, NY), con un panel en tiempo real pensado para mostrarse en una
tablet del restaurante.

## 📍 Estado del proyecto (para retomarlo en cualquier momento)

**Ubicación permanente del proyecto:**
`/Users/mgabriella98/WhiteBearRest.PROYECT./white-bear-reservations`

**Para arrancarlo:**
```bash
cd "/Users/mgabriella98/WhiteBearRest.PROYECT./white-bear-reservations"
python3 server.py 8123
```
Luego abre `http://localhost:8123/` (clientes) o `http://localhost:8123/tablet.html`
(staff). Desde el celular en la misma red Wi-Fi, usa la IP de esta Mac en vez
de `localhost` (correr `ipconfig getifaddr en0` para obtenerla).

**✅ Ya construido y probado:**
- Formulario de reservaciones con validación de horario por día y tamaño de grupo.
- Panel de tablet en tiempo real (se actualiza solo, sin recargar).
- Preorden para grupos de 20+ personas (menú aún placeholder, ver más abajo).
- Confirmación y recordatorio automático por SMS/correo (modo prueba, sin credenciales reales todavía).
- Ventana emergente de confirmación de asistencia (24h o 30 min antes).
- Paleta de colores verde/marrón/vinotinto (la real del restaurante) + sección "Información del lugar" con accesibilidad, estacionamiento, mascotas, etc.
- Idiomas: sitio de clientes en EN/ES/FR (inglés por defecto); panel de tablet en EN/ES/SR (inglés por defecto).
- Repositorio Git local con todo el historial de cambios (7 commits al día de hoy).

**⏳ Pendiente para que el proyecto esté 100% terminado:**
1. **Publicarlo en internet** — está listo para Render.com (ver sección más abajo), solo falta crear la cuenta de GitHub/Render y hacer el push (yo no puedo crear esas cuentas, pero sí ejecutar los comandos si me das la URL del repo).
2. **Menú real para el preorden de grupos grandes** — hoy son 3 platillos placeholder.
3. **Credenciales reales de SMS/correo** (Twilio + SMTP) — hoy todo funciona en modo simulado.
4. **Almacenamiento persistente** antes de recibir reservaciones reales de producción (ver advertencia sobre Render más abajo).
5. Decidir si el panel de tablet necesita más idiomas o queda así.

Dime en qué de esto quieres que sigamos y retomamos justo ahí.

## Qué incluye

- **`public/index.html`** — página para que los clientes reserven mesa (nombre,
  teléfono, correo opcional, fecha, hora, número de personas, ocasión y notas).
- **`public/tablet.html`** — panel para el staff, optimizado para tablet:
  se actualiza solo cada 5 segundos, agrupa por Hoy / Próximas / Todas,
  filtra por estado (pendiente, confirmada, etc.) y permite avanzar cada
  reservación con botones grandes: Confirmar → Sentar → Finalizar, o Cancelar.
- **`server.py`** — backend en Python (sin dependencias externas) que valida
  las reservaciones (horario del restaurante, tamaño de grupo, fecha no
  pasada) y las guarda en `data/reservations.json`. Como cliente y tablet
  hablan con el mismo servidor, cualquier reservación nueva aparece en la
  tablet automáticamente, sin recargar la página.
- **`notifications.py`** — envía el mensaje de confirmación al crear la
  reservación y un recordatorio automático 15 minutos antes de la hora
  reservada, por SMS y/o correo. Ver sección de abajo.

## Confirmación y recordatorio automático (SMS / correo)

Al crear una reservación se envía un mensaje de confirmación por SMS (al
teléfono, siempre) y por correo (si el cliente lo dejó). Un proceso en
segundo plano revisa cada minuto las reservaciones próximas y, 15 minutos
antes de la hora reservada, envía un aviso de "tu mesa está casi lista" por
los mismos canales. Cada reservación se recuerda solo una vez
(`reminderSent` en el registro evita duplicados), y las reservaciones
canceladas no reciben recordatorio.

**Mientras no configures credenciales reales, el envío funciona en modo de
prueba ("dry-run"):** los mensajes no salen de verdad, pero se registran en
`data/notifications_log.txt` y en la consola del servidor, para que puedas
ver exactamente qué se habría enviado y a quién. Así puedes probar todo el
flujo (crear reservación → confirmación → recordatorio) sin depender de
ningún proveedor.

Para activar el envío real, define estas variables de entorno antes de
correr `server.py` (por ejemplo con `export VARIABLE=valor` en la terminal,
o configurándolas en el panel de tu hosting cuando lo despliegues):

**Correo (cualquier proveedor SMTP; ejemplo con Gmail y una "contraseña de
aplicación", no la contraseña normal de la cuenta):**
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=turestaurante@gmail.com
SMTP_PASSWORD=xxxxxxxxxxxxxxxx
SMTP_FROM=turestaurante@gmail.com
```

**SMS (requiere una cuenta gratuita/de prueba en [twilio.com](https://twilio.com)):**
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+15005550006
```

No hace falta configurar los dos — puedes activar solo correo, solo SMS, o
ambos. Al arrancar, el servidor imprime en consola si cada canal está
ACTIVO o en modo prueba.

## Confirmación de asistencia ("ventana emergente")

Además de la confirmación de la reservación, el sitio pide que el cliente
**confirme su asistencia** antes de la hora reservada:

- **Reservaciones hechas con días de anticipación:** se les pide confirmar
  **24 horas antes** de la hora reservada.
- **Reservaciones hechas el mismo día:** se les pide confirmar **30 minutos
  antes**.

El aviso llega por SMS y/o correo (los mismos canales configurados arriba)
con un link a `confirm.html?id=<código>` — una página que se ve y se
comporta como una ventana emergente, con dos botones: **"Sí, confirmo mi
asistencia"** o **"No podré asistir"**. Si confirma, queda marcado
`attendanceConfirmed: true` y se ve en la tablet con la etiqueta "✅
Asistencia confirmada". Si dice que no podrá asistir, la reservación se
cancela automáticamente. **Si la persona no responde**, el mensaje le indica
que debe llamar al restaurante al (518) 302-5235; mientras tanto, esa
reservación aparece en la tablet con la etiqueta "⏳ Esperando confirmación"
y en la pestaña de filtro **"Por confirmar"**, para que el staff sepa a
quién llamar.

Cada reservación solo recibe esta solicitud una vez
(`attendanceReminderSent` evita duplicados) y las canceladas no la reciben.

**Importante sobre el link:** el mensaje arma la URL usando
`PUBLIC_BASE_URL` (o `http://localhost:PUERTO` si no la defines). Al
desplegar el sitio en internet, define esta variable de entorno con tu URL
real (por ejemplo `https://white-bear-reservations.onrender.com`) para que
el link del SMS/correo funcione desde cualquier celular.

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

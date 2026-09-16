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

**🌐 En vivo:** https://whitebearrestaurantreservation.onrender.com
(repo: https://github.com/franjivar2502/whitebearrestaurantreservation)

**✅ Ya construido y probado:**
- Formulario de reservaciones con validación de horario por día y tamaño de grupo.
- Panel de tablet en tiempo real (se actualiza solo, sin recargar).
- Preorden para grupos de 20+ personas (menú aún placeholder, ver más abajo).
- Confirmación y recordatorio automático por SMS/correo (modo prueba, sin credenciales reales todavía).
- Ventana emergente de confirmación de asistencia (24h o 30 min antes).
- Paleta de colores verde/marrón/vinotinto (la real del restaurante) + sección "Información del lugar" con accesibilidad, estacionamiento, mascotas, etc.
- Idiomas: sitio de clientes en EN/ES/FR (inglés por defecto); panel de tablet en EN/ES/SR (inglés por defecto).
- Galería de fotos con pantalla de bienvenida (fondo de 1 segundo al entrar) y panel de administración para agregar/reordenar/eliminar fotos (`/admin-photos.html`, ver sección más abajo).
- **Persistencia vía Supabase ya conectada y verificada en producción** (`storage.py`) — las reservaciones y fotos ya no se pierden cuando Render reinicia el servicio.
- Repositorio en GitHub, desplegado en Render y funcionando en vivo (probado el 2026-09-16): https://whitebearrestaurantreservation.onrender.com

**🔧 Bugs reales encontrados y corregidos (2026-09-16):**
- Typo en el valor de la variable de entorno `SUPABASE_URL` en Render (tenía el texto literal "SUPABASE_URL" en vez de la URL real).
- La clave `SUPABASE_KEY` se pegó mal en Render (se copió la versión enmascarada del campo — puntos en vez del texto real). Ahora `storage.py` detecta esto automáticamente y da un mensaje de error específico si vuelve a pasar.
- La pantalla de bienvenida (`welcome-splash`) se quedaba trabada en pantalla para siempre cuando la galería no tenía fotos (bug de CSS `display:flex` anulando `[hidden]`, combinado con que el JS solo la ocultaba dentro de la rama "hay fotos"). Ya corregido para que siempre se oculte tras 1 segundo, haya o no fotos.

**⏳ Pendiente para que el proyecto esté 100% terminado:**
1. **Menú real para el preorden de grupos grandes** — hoy son 3 platillos placeholder.
2. **Credenciales reales de SMS/correo** (Twilio + SMTP) — hoy todo funciona en modo simulado.
3. **Cambiar `ADMIN_PASSWORD`** (panel de fotos) a una contraseña definitiva — hoy sigue siendo la de prueba (`whitebear123`).
4. Decidir si el panel de tablet necesita más idiomas o queda así.
5. Volver a agregar al menos una foto real a la galería (se vació durante las pruebas de Supabase).
6. **Próxima sesión: pulir el sitio a nivel visual/UX ("nivel app de $10k")** — ver la lista de mejoras preparada para la siguiente sesión.

Dime en qué de esto quieres que sigamos y retomamos justo ahí.

## 🎨 Plan de mejora visual/UX — próxima sesión ("nivel app de $10k")

Lo funcional ya está sólido (reservaciones, tablet, notificaciones,
persistencia real). Lo que separa esto de una app pulida de verdad es
sobre todo **acabado visual, detalles de interacción y presencia
profesional** — no funciones nuevas. Orden sugerido, de mayor a menor
impacto visible para el cliente final:

1. **Tipografía real.** Hoy usa la fuente del sistema. Un par de fuentes
   de Google Fonts (una para títulos, otra para texto) cambia por
   completo la sensación de "hecho a mano" a "diseñado".
2. **Estados de carga y vacío diseñados.** Ahora mismo un formulario
   enviándose o una galería sin fotos se ven simplemente en blanco.
   Agregar spinners/skeletons y mensajes de "aún no hay fotos" con
   estilo, en vez de espacios vacíos.
3. **Micro-interacciones.** Transiciones suaves en botones, hover states,
   feedback visual al confirmar una reservación (no solo un mensaje de
   texto). Esto es lo que más "se siente" en una app pulida.
4. **Meta tags para compartir (Open Graph).** Ahora mismo si alguien
   comparte el link en WhatsApp/Facebook no se ve ninguna vista previa
   con imagen. Agregar `og:image`, `og:title`, `og:description` y un
   favicon real (hoy no tiene).
5. **Mapa embebido** con la ubicación real (2793 Wilmington Rd), en vez
   de solo la dirección en texto.
6. **Sección de reseñas/calificación más visual** — hoy el 4.2 (243
   reseñas) aparece como texto plano; se puede mostrar con estrellas y
   más presencia, ya que es un dato de confianza real y verificable.
7. **Optimización de imágenes** (compresión, tamaños responsivos) para
   que la galería cargue rápido incluso en el "cold start" de Render.
8. **Revisión de accesibilidad** — contraste de colores, estados de foco
   visibles con teclado, textos alternativos en imágenes.
9. **Dominio propio** (ej. `reservas.whitebearrestaurant.com`) en vez de
   `onrender.com` — decisión de negocio del cliente, no técnica, pero
   cambia mucho la percepción de profesionalismo.
10. Pulir visualmente el panel de administración de fotos y el de tablet
    (hoy son funcionales pero muy utilitarios).

No implementar nada de esto todavía — es la lista para retomar en la
próxima sesión.

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

## Persistencia de datos (Supabase)

Render borra el disco local cada vez que el servicio se reinicia (se duerme
por inactividad y despierta), así que las reservaciones guardadas en
`data/reservations.json` se pierden. `storage.py` resuelve esto usando
Supabase (Postgres gratis, vía su API REST) cuando está configurado, y cae
de vuelta al archivo local si no lo está — no hace falta ninguna librería
nueva, solo `urllib` de la librería estándar.

**Para activarlo:**

1. Crea una cuenta gratis en [supabase.com](https://supabase.com) y un
   proyecto nuevo.
2. En **SQL Editor**, corre:
   ```sql
   create table reservations (
     id text primary key,
     data jsonb not null,
     created_at timestamptz not null default now()
   );

   create table photos (
     id text primary key,
     url text not null,
     caption text not null default '',
     sort_order integer not null default 0,
     created_at timestamptz not null default now()
   );
   ```
3. En **Settings → API**, copia la **Project URL** y la **service_role**
   key (la secreta, no la "anon/public").
4. Define estas variables de entorno donde corra `server.py` (local o en
   Render):
   ```
   SUPABASE_URL=https://xxxxxxxx.supabase.co
   SUPABASE_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

Sin esas variables, todo sigue funcionando igual que antes con el archivo
local (útil para desarrollo, pero no para producción en Render).

## Galería de fotos y pantalla de bienvenida

El sitio de clientes (`index.html`) puede mostrar fotos reales del
restaurante:

- Si hay al menos una foto cargada, al entrar al sitio aparece una
  **pantalla de bienvenida** de 1 segundo con la primera foto como fondo,
  antes de revelar el resto de la página.
- Todas las fotos se muestran además en una sección **"Gallery"** normal
  dentro de la página.
- Sin fotos cargadas, el sitio se ve exactamente igual que antes (sin
  pantalla de bienvenida, sin sección de galería).

**Panel de administración:** `/admin-photos.html` — protegido por
contraseña. Ahí puedes **agregar** (pegando la URL de una imagen),
**reordenar** (↑/↓ — la primera foto es la que se usa de fondo de
bienvenida) y **eliminar** fotos, sin tocar código.

Para activarlo, define esta variable de entorno (elige una contraseña
real, no la de ejemplo):
```
ADMIN_PASSWORD=una-contraseña-que-solo-tú-sepas
```
Sin esta variable configurada, el panel de administración queda
bloqueado por completo (nadie puede agregar/borrar fotos, ni siquiera con
la contraseña en blanco).

**Sobre las URLs de las fotos:** el servidor no tiene un sistema propio de
"subir archivos" (para mantenerlo sin dependencias), así que cada foto se
agrega pegando la URL de una imagen que ya esté alojada en algún lado:

- Sube el archivo al **Storage** de Supabase (gratis, 1GB) y copia el link
  público — es la opción más prolija ya que usamos Supabase de todos modos.
- O cualquier otro host de imágenes (Imgur, un link público de Google
  Drive/Fotos, etc.).

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

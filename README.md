# White Bear Restaurant — Reservaciones

Sitio de reservaciones online para White Bear Restaurant (2793 Wilmington Rd,
Lake Placid, NY), con un panel en tiempo real pensado para mostrarse en una
tablet del restaurante.

## 📍 Estado del proyecto (para retomarlo en cualquier momento)

**Ubicación permanente del proyecto (original):**
`/Users/mgabriella98/WhiteBearRest.PROYECT./white-bear-reservations`

**⚠️ Hay dos copias del proyecto en esta Mac.** La que se usa a diario es
`/Users/mgabriella98/whitebearrestaurantreservation`; ya tiene acceso de
escritura a GitHub mediante una llave SSH dedicada (`~/.ssh/id_ed25519_whitebear`,
con el alias `github.com-whitebear` en `~/.ssh/config`). **Antes de ponerse a
trabajar en cualquiera de las dos, hacer `git pull`**, o se pierden cambios
hechos en la otra.

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
- **Disponibilidad real por asientos** (128 en 25 mesas) — una reservación se rechaza si no hay suficientes asientos libres a esa fecha/hora, considerando reservaciones ya activas y mesas que el staff marcó fuera de servicio. Ver sección "Mesas y disponibilidad real" más abajo.
- Preferencia de mesa adentro/afuera (opcional) en el formulario de reservación.
- Panel de tablet en tiempo real (se actualiza solo, sin recargar), con una pestaña nueva "Tables"/"Mesas" para que el staff marque mesas fuera de servicio.
- Confirmación y recordatorio automático por SMS/correo (modo prueba, sin credenciales reales todavía).
- Ventana emergente de confirmación de asistencia (24h o 30 min antes).
- Diseño visual pulido: tipografía real (Fraunces + Inter), favicon propio, meta tags para compartir en redes, mapa embebido, calificación con estrellas, fondo tipo "marca de agua" con foto real del comedor, secciones desplegables (Our Menu/Reviews/Find us/Venue information), micro-interacciones, y un pequeño distintivo "Built with AI" en el pie de página.
- **Logo real del oso** (`public/images/bear-logo.jpg` + `public/favicon.png`) en vez del emoji 🐻‍❄️ — un sello circular con el nombre del restaurante, generado específicamente para el negocio (no es foto de stock). Se usa como ícono de marca en las 5 páginas del sitio y como favicon (recortado a la cara del oso para que se lea bien de pequeño). Si se quiere cambiar, basta con reemplazar `bear-logo.jpg` por otra imagen cuadrada.
- Idiomas: sitio de clientes en EN/ES/FR (inglés por defecto); panel de tablet en EN/ES/SR (inglés por defecto).
- Fotos del menú con pantalla de bienvenida (fondo de 1 segundo al entrar) y panel de administración para agregar/reordenar/eliminar fotos (`/admin-photos.html`, ver sección más abajo).
- **Secciones "About us" y "Gallery" y preorden de grupos eliminados del sitio (2026-10-05)**, a pedido del cliente. El sitio público solo muestra la galería "Our Menu"; el panel de fotos (`/admin-photos.html`) ya solo agrega fotos del menú (sin selector de sección). Las fotos viejas de la sección "gallery" siguen en la base pero no se muestran; el panel las marca como "Sin mostrar en el sitio" y trae un botón "＋ Menú" para pasarlas al menú.
- **Reseñas de clientes con fotos**, moderadas automáticamente (`public/js/app.js` + `server.py`) — cualquier visitante puede dejar una reseña con calificación de 1 a 5 estrellas y subir una foto directo desde su celular. Cualquier reseña que contenga una palabra clave negativa (lista en `NEGATIVE_REVIEW_KEYWORDS` en `server.py`) no se publica sola: se guarda como pendiente y aparece en la sección "Reseñas de clientes" de `/admin-photos.html`, donde el staff la publica o la oculta (ocultar no la borra). Al cliente se le avisa que el equipo la leerá y se le invita a llamar. El resto se publica al instante; la calificación en estrellas no influye. Las fotos se guardan en Supabase Storage (bucket `review-photos`, ya creado) o en `public/uploads/reviews/` en desarrollo local sin Supabase.
- **Persistencia vía Supabase ya conectada y verificada en producción** (`storage.py`) — las reservaciones, fotos, reseñas y estado de mesas ya no se pierden cuando Render reinicia el servicio.
- Repositorio en GitHub, desplegado en Render y funcionando en vivo: https://whitebearrestaurantreservation.onrender.com

**⏳ Pendiente para que el proyecto esté 100% terminado:**
1. **Credenciales reales de SMS/correo** (Twilio + SMTP) — hoy todo funciona en modo simulado.
2. ~~Cambiar `ADMIN_PASSWORD`~~ — **hecho (2026-10-03).** La contraseña está
   solo en las variables de entorno de Render y no se escribe en ningún
   archivo del repositorio. Si hace falta consultarla: Render → el servicio →
   Environment → el icono del ojo. **Nunca la pegues aquí**: este repositorio
   es público.
   **Falta `STAFF_PASSWORD`** (contraseña del panel de tablet, ver "Acceso del
   staff" más abajo): definirla en Render igual que la de administración.
3. **Cuadrar los dos asientos que bailan.** El plano se revisó con el cliente
   el 2026-10-02 (se quitó la mesa 18, las 23/24/25 pasaron a 6 asientos y las
   9/10 a 4) y queda en **128**. El cliente dice 130 de palabra, así que falta
   encontrar dos sillas en alguna parte -- o confirmar que su cifra incluye la
   barra. La numeración tiene un hueco en el 18: queda así a propósito, para no
   cambiarle el rótulo a ocho mesas si el personal ya las llama por su número.
4. **Fotos del comedor y el exterior:** la sección "Gallery" se eliminó del sitio, así que ya no hacen falta. Las **6 del menú ya
   están** subidas (`public/images/menu/`, 2026-10-01) y se ven tanto en
   "Our Menu" como en el carrusel junto al formulario. La de los mejillones
   vino a 384x512, muy por debajo de las otras cinco: si el cliente tiene el
   original, conviene reemplazarla. Aviso para la próxima tanda: las fotos
   exportadas desde Fotos.app en macOS son archivos temporales protegidos por
   el sistema y no se pueden leer -- hay que pedirle que las guarde en
   Escritorio o Descargas.
5. Revisar y ampliar `NEGATIVE_REVIEW_KEYWORDS` en `server.py` si empiezan a
   llegar reseñas reales -- la lista actual es un punto de partida, no es
   exhaustiva. **Importante:** las palabras se buscan por palabra completa, no
   por subcadena. Si se vuelve a buscar por subcadena, "rat" bloquea "trato" y
   se retienen reseñas buenas (pasó, ver DURABILIDAD.md).
6. Decidir si el panel de tablet necesita más idiomas o queda así.
7. **Leer `DURABILIDAD.md`** antes de hablar de mantenimiento con el cliente:
   ahí está qué hace falta para que esto siga en pie dentro de diez años, y el
   aviso sobre la norma de la FTC en materia de reseñas.

8. **Políticas legales (`public/legal.html`) — borrador.** Privacidad,
   condiciones de reserva, condiciones de SMS/correo, política de reseñas y
   fotos, y accesibilidad, en EN/ES/FR. Antes de publicarlas: completar cada
   `<mark class="fill">` (razón social, correo de contacto, fecha, plazos),
   que las revise un abogado de Nueva York y quitar el aviso de borrador.
   Ojo: la política de reseñas dice que no se ocultan las negativas, así que
   no puede salir antes que el cambio de moderación de reseñas (PR #2).

Dime en qué de esto quieres que sigamos y retomamos justo ahí.

## 🎨 Sistema de diseño — "Lake Placid Ivory" (2026-09-30)

La paleta y la tipografía **no son inventadas**: salen de analizar cómo se
presentan los restaurantes de lujo y los hoteles de la zona. Se midieron los
estilos computados de cuatro sitios de referencia:

| Sitio | Ancla oscura | Fondo | Acento | Display | Texto |
|---|---|---|---|---|---|
| Mirror Lake Inn (Lake Placid, AAA 4 diamantes) | verde `#222E22` | marfil `#FEFAF2` | salvia `#617A61` | Orpheus Pro | Outfit |
| Lake Placid Lodge | marino `#002045` | `#F5F5F2` | salvia `#D2E8D1` | Minerva | Synonym |
| The Point (Adirondacks) | negro | marfil `#FFF8ED` | champán `#EDC787` | Cinzel | Quattrocento |
| Eleven Madison Park | casi negro | blanco | ninguno | EB Garamond | nobel |

Lo que comparten y se aplicó aquí: fondo claro y cálido, **un solo** color
profundo y desaturado como ancla, acento apagado usado con cuentagotas, un
serif de estilo antiguo para los títulos, y casi nada de color en la interfaz
— el color fuerte lo ponen las fotos del restaurante.

Tokens (definidos en `public/css/style.css`, el panel los hereda):

- Fondo `#fbf9f4` marfil · tinta `#1c2420` · apagado `#5f6b60`
- **Ancla: verde bosque `#20301f`** — es el color de los botones. Ya estaba en
  la marca de White Bear, así que la paleta no es prestada.
- **Acento: latón `#7e6433`** — el oro anterior (`#d9a441`) a media saturación;
  solo aparece en los títulos de sección y en las estrellas de reseña.
- Los neutros van sesgados hacia el verde del ancla, no son grises puros.
- Display **EB Garamond**, texto **Outfit**. No hay tercera fuente: las cifras
  que se alinean usan `font-variant-numeric: tabular-nums` sobre Outfit.

**Fondo 3D** (`public/js/bg-3d.js`): un amanecer brumoso de los Adirondacks en
WebGL, sin librerías (~4KB en vez de ~600KB de Three.js, que en el plan gratis
de Render se nota en el arranque en frío). Cuatro cordilleras en perspectiva
aérea y bancos de niebla. **La versión con aurora boreal y estrellas sobre
cielo negro se retiró a propósito**: hacía que el sitio pareciera un local
nocturno, y ninguna de las referencias pone luces de colores detrás del
contenido.

Si se vuelve a tocar el tema, respetar dos cosas: el acento se gasta en un
solo sitio, y todo par de texto tiene que pasar 4.5:1 (hay un script de
auditoría de contraste en el historial de la sesión).

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

- **Se reservan mesas a cualquier hora, cualquier día (24/7).** El servidor
  no rechaza una reserva por caer fuera del horario de apertura, y el campo
  de hora del formulario no tiene tope ni por arriba ni por abajo.
- El horario publicado (lunes a jueves y domingo 11:00 a.m. – 9:00 p.m.;
  viernes y sábado 11:00 a.m. – 9:30 p.m.) se sigue mostrando en el sitio,
  pero como **información para el cliente**, no como una regla que rechace
  la reserva.
- Grupos de 1 a 40 personas (para grupos más grandes se sugiere llamar).
- No se permiten fechas pasadas, ni más de 6 meses de anticipación.
- Lo que sí limita una reserva: los asientos libres a esa hora (ver "Mesas
  y disponibilidad real") y el interruptor de reservaciones del panel (ver
  "Acceso del staff").

Estos valores están en el diccionario `RESTAURANT` al inicio de `server.py`.
Si algún día se quiere volver a cerrar la reserva fuera de horario, hay que
reponer la validación en `_validate_reservation` (hoy lleva un comentario
en el sitio exacto donde iba) y devolver los `min`/`max` al campo de hora
en `public/js/app.js` y `public/js/tablet.js`.

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

   create table table_status (
     id text primary key,
     data jsonb not null,
     created_at timestamptz not null default now()
   );

   create table reviews (
     id text primary key,
     data jsonb not null,
     created_at timestamptz not null default now()
   );

   create table settings (
     id text primary key,
     data jsonb not null,
     created_at timestamptz not null default now()
   );

   insert into storage.buckets (id, name, public)
   values ('review-photos', 'review-photos', true)
   on conflict (id) do nothing;
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

## Mesas y disponibilidad real

El sitio ya sabe cuántos asientos hay libres a la hora que alguien está
reservando -- no deja pasar una reservación que no cabe.

**Inventario de mesas** (en `TABLE_LAYOUT` de `server.py`, revisado con el
cliente sobre el plano el 2026-10-02): 10 cuadradas de 4, 6 rectangulares de
4, 7 rectangulares de 6, 1 rectangular de 10 y 1 rectangular de 12 --
**128 asientos en total** (25 mesas). Las 11 banquetas de la barra se dibujan
en el plano pero NO suman aforo: la barra se ocupa sin reserva. Cada mesa lleva además en qué salón está y su posición en el
plano. Si cambia el número de mesas, las sillas, o dónde está una mesa,
edita `TABLE_LAYOUT` -- es el único lugar.

**Cómo se calcula la disponibilidad:** en vez de exigir una mesa exacta
del tamaño del grupo, se suman los asientos libres -- así una reserva de
8 personas puede usar dos mesas de 4 juntas, tal como el restaurante
acomoda de verdad. Una reservación nueva se compara contra: la capacidad
total, menos las mesas que el staff marcó "no disponible" en el panel,
menos lo ya comprometido por otras reservaciones activas cuyo horario se
cruza (cada reservación ocupa su mesa 90 minutos, editable en
`RESERVATION_DURATION_MINUTES`). Si no alcanza, el sitio de clientes
rechaza la reservación con un mensaje claro en vez de aceptarla a ciegas.

**Panel de staff (`tablet.html` → pestaña "Tables"/"Mesas"):** un plano
de los dos salones como están en el local, con la barra, la entrada, el
baño y las ventanas, y cada mesa en su lugar -- el staff la busca por
dónde está parada, no leyendo una lista. Tocar una mesa la marca
disponible/no disponible (por ejemplo, para un evento privado o una
silla rota) y eso baja la capacidad que ve el sitio de clientes al
instante; las fuera de servicio van en rojo y tachadas, para que no
dependa solo del color. Como todo el panel de tablet, pide la contraseña
de staff (ver "Acceso del staff").

## Acceso del staff (panel de tablet)

Las reservaciones guardan nombre y teléfono de cada cliente, así que el
panel de tablet (`/tablet.html`) y la API privada piden una contraseña.
Al abrir el panel aparece una pantalla de acceso; una vez dentro, la
tablet la recuerda (en el navegador de ese dispositivo) y no la vuelve a
pedir hasta que la contraseña cambie en el servidor.

Para activarlo, define esta variable de entorno (en Render: **Environment**):
```
STAFF_PASSWORD=una-contraseña-para-el-personal
```
Si no se define, el panel acepta la de `ADMIN_PASSWORD`; si no hay
ninguna de las dos, el panel queda bloqueado por completo. La contraseña
de administración siempre abre también el panel de staff.

**Qué queda protegido:** ver la lista de reservaciones
(`GET /api/reservations`), cambiar su estado o borrarlas
(`PATCH`/`DELETE /api/reservations/<id>`), ver o marcar mesas
(`/api/tables`), y encender o apagar las reservaciones
(`GET`/`PATCH /api/settings`). **Qué sigue público, a propósito:** reservar
(`POST /api/reservations`), la página de confirmación de asistencia a la
que llega el cliente desde su SMS/correo (`/api/reservations/<id>` y
`.../confirm-attendance`, que solo funcionan con el código de esa
reservación), el menú, las fotos y las reseñas.

### Apagar las reservaciones (interruptor del panel)

En la barra del panel, junto a "Nueva reservación", hay un botón con un
punto de color que dice **Reservaciones activas** / **Reservaciones
apagadas**. Sirve para cerrar la agenda al público cuando no se quieren
más reservaciones: noche de evento privado, cocina saturada, obra en el
salón. Pide confirmación antes de cambiar, porque en una tablet de salón
un roce basta para tocarlo.

Con el interruptor apagado:

- El formulario del sitio de clientes se deshabilita y muestra un aviso con
  el teléfono del restaurante, en vez de dejar que el cliente lo llene para
  recibir un error al enviarlo.
- `POST /api/reservations` responde `403` con el código `BOOKING_CLOSED`
  para cualquiera que no mande la contraseña de staff.
- **El alta rápida del panel sigue funcionando**: apagar el interruptor es
  cerrar la agenda al público, no impedir que el encargado apunte la mesa
  que acaba de entrar por teléfono.
- Las reservaciones ya tomadas no se tocan: siguen en la lista del turno.

El estado se guarda en el servidor (tabla `settings` de Supabase, o
`data/settings.json` en local), así que sobrevive a un reinicio y lo ven
todas las tablets: el panel lo relee cada 5 segundos, de modo que si
alguien lo apaga desde otro dispositivo, los demás se enteran solos. Por
omisión está encendido.

## Seguridad del sitio

Lo que el servidor hace solo, sin configurar nada (`security.py` y `server.py`):

- **Fuerza bruta:** 10 contraseñas de staff/admin equivocadas desde la
  misma conexión bloquean esa conexión 15 minutos (responde 429, también si
  después acierta). El resto de conexiones sigue entrando normal.
- **Spam:** como mucho 10 reservaciones por hora y 5 reseñas por hora desde
  la misma conexión (la tablet del staff no tiene tope). Ambos formularios
  llevan un campo trampa invisible que solo llenan los bots.
- **Códigos de reservación:** los nuevos son de 32 caracteres (imposibles de
  adivinar); al cliente se le muestra solo el inicio. Con el código solo se
  ve nombre, fecha, hora y personas, nunca teléfono ni correo, y las
  consultas por código tienen tope por conexión.
- **Fotos de reseñas:** se acepta un archivo solo si su contenido es de
  verdad JPG, PNG, GIF o WebP (no basta con la extensión).
  Antes de publicarla se le quita la ubicación GPS que guardan los
  celulares (se conserva la orientación, para que no salga de lado).
- **Consentimiento:** cada reservación hecha desde el sitio guarda que el
  cliente aceptó las condiciones y los SMS, con la versión del texto
  (`LEGAL_TERMS_VERSION` en `server.py`, cambiarla cuando cambie
  `legal.html`) y la hora. Las reseñas guardan lo mismo. Las reservas que
  apunta el staff por teléfono quedan marcadas como `"source": "staff"`.
- **Cabeceras:** política de contenido (solo se ejecutan scripts del propio
  sitio), prohibido meter el sitio en un iframe, `nosniff`, HSTS en https.
- **Peticiones:** tope de tamaño del cuerpo, conexiones mudas cortadas a los
  30 s, y se rechazan las que modifican datos desde otro sitio web.
- **Errores:** el navegador recibe un mensaje genérico; el detalle va solo
  al log de Render.

Lo que depende del dueño: contraseñas largas (12+ caracteres, el servidor
avisa al arrancar si son cortas) y distintas para `STAFF_PASSWORD` y
`ADMIN_PASSWORD`, y no compartir la de admin con el personal de sala.

## Galería de fotos y pantalla de bienvenida

El sitio de clientes (`index.html`) puede mostrar fotos reales del
restaurante:

- Si hay al menos una foto cargada, al entrar al sitio aparece una
  **pantalla de bienvenida** de 1 segundo con la primera foto como fondo,
  antes de revelar el resto de la página.
- Toda foto nueva se agrega como foto del **menú** y se muestra en **"Our Menu"**
  y en el carrusel junto al formulario, en el orden de la lista. La sección
  "Gallery" del sitio público se eliminó (2026-10-05); las fotos viejas marcadas
  como "gallery" no se muestran hasta pasarlas al menú con el botón "＋ Menú".
- Sin fotos cargadas, el sitio se ve exactamente igual que antes (sin
  pantalla de bienvenida, sin sección de menú).

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

## Operación, respaldos y pruebas

Todo lo necesario para mantener el sitio en pie (variables de entorno,
monitoreo con `/healthz`, respaldos diarios cifrados, limpieza de datos,
dominio propio y qué hacer si algo falla) está en **`OPERACION.md`**.

Pruebas automáticas, sin instalar nada:

```bash
python3 -m unittest discover -s tests -v
```

## Otros siguientes pasos sugeridos

- Añadir notificación por correo/SMS al restaurante cuando llega una
  reservación nueva.
- Resolver el almacenamiento persistente (ver arriba) antes de usarlo en
  producción.

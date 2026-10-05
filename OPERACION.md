# Operación y mantenimiento

Guía para quien tenga que mantener el sitio de White Bear Restaurant en pie:
qué configurar, cómo vigilarlo, cómo sacar y restaurar copias, y qué hacer
cuando algo falla. `DURABILIDAD.md` explica el *por qué*; este documento es
el *cómo*.

---

## 1. Lo que el sistema ya hace solo

- **No vende la misma mesa dos veces.** La comprobación de asientos libres y
  el guardado de la reservación ocurren en un solo paso. Antes eran dos, y dos
  clientes reservando el último hueco a la vez entraban los dos (hay una
  prueba que lo demuestra: `test_concurrent_bookings_never_exceed_capacity`).
- **Usa la hora de Lake Placid**, no la del servidor (que está en UTC). Antes,
  a partir de las 8 de la noche el servidor creía que ya era mañana y los
  recordatorios salían con 4-5 horas de desfase.
- **Lee todas las filas de Supabase.** Supabase entrega como máximo 1000 filas
  por consulta; a partir de la reservación 1001 las nuevas dejaban de verse en
  la tablet y de contar para la disponibilidad. Ahora se pide página a página.
- **Reintenta los fallos pasajeros de Supabase** (red caída un segundo,
  sobrecarga) dos veces antes de rendirse.
- **No corrompe los archivos locales** si el proceso muere a mitad de una
  escritura, y si encuentra uno dañado lo aparta (`*.corrupt-<fecha>`) en vez
  de sobrescribirlo.
- **Avisa de sus errores en el log** (Render → Logs, líneas `[ERROR]`). Antes
  el hilo de recordatorios se tragaba los errores en silencio.
- **Expone `/healthz`**, una página que responde 200 si todo está bien y 503
  si el almacenamiento no responde. Es lo que miran los monitores.

---

## 1b. Apagar las reservaciones desde el panel del staff

En la barra del panel (junto a "Nueva reservación") hay un botón con un punto
de color: **Reservaciones activas** / **Reservaciones apagadas**. Apagado, el
formulario del sitio de clientes se deshabilita con el teléfono del local y el
servidor rechaza las reservaciones nuevas que vengan de internet. El alta
rápida del panel y las reservaciones ya tomadas no se tocan. Pide
confirmación antes de cambiar, y el estado se guarda en la tabla `settings`
de Supabase, así que sobrevive a reinicios y lo ven todas las tablets.

El sitio siempre está en línea; ya no hay pestaña "Sitio web" ni modo "cerrado
temporalmente". Las reservaciones solo se aceptan dentro del horario de
apertura, hasta 15 minutos antes del cierre (ver README, "Horario y reglas").

---

## 2. Variables de entorno (Render → el servicio → Environment)

| Variable | Obligatoria | Para qué |
|---|---|---|
| `SUPABASE_URL` | Sí | URL del proyecto de Supabase (`https://xxxx.supabase.co`). Sin ella los datos se pierden en cada reinicio. |
| `SUPABASE_KEY` | Sí | Clave `service_role` de Supabase. **Secreta.** |
| `ADMIN_PASSWORD` | Sí | Contraseña del panel de fotos (`/admin-photos.html`). |
| `STAFF_PASSWORD` | Sí, cuando se active el acceso del personal | Contraseña de la tablet. |
| `PUBLIC_BASE_URL` | Sí | La dirección pública del sitio, para los enlaces de los SMS. Cámbiala al estrenar dominio propio. |
| `RESTAURANT_TIMEZONE` | No | Zona horaria del restaurante. Por defecto `America/New_York`. |
| `RESERVATION_RETENTION_DAYS` | No | Días que se guardan las reservaciones pasadas (60 si no se define). Ver sección 6. |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` | Para SMS reales | Sin ellas los SMS solo se simulan. |

Nunca escribas ninguno de estos valores en el repositorio: es público.

### Activar los mensajes de confirmación (solo SMS)

El código ya está listo; solo faltan las credenciales, que se ponen como
variables de entorno en Render (nunca en el repositorio). Mientras falten, los
mensajes se "simulan": se escriben en los logs de Render (`DRY-RUN`) y no
sale nada.

**Qué se envía:** al reservar, un mensaje de confirmación; el día anterior (o
30 minutos antes si la reserva es del mismo día), un enlace para confirmar
asistencia; y 15 minutos antes, el aviso de mesa lista. Va solo por SMS, al
teléfono del cliente (no se envía correo).

**Idioma:** cada mensaje sale en el idioma con que el cliente llenó el formulario
(inglés, español o francés), con la fecha y la hora escritas con claridad
("lunes 12 de octubre a las 7:00 p.m."). El enlace de confirmación de asistencia
abre la página en ese mismo idioma. En el alta rápida del panel hay un selector
**Idioma del mensaje** (inglés por omisión), para las reservas por teléfono. Lo
que no traiga idioma (reservas anteriores) se envía en inglés. Los SMS van sin
acentos para que quepan en un solo mensaje. Los textos
están en `MESSAGES`, en `notifications.py`.

**SMS (Twilio):**
1. Crear la cuenta en twilio.com y comprar un número de EE. UU.
2. **Registrar el envío para EE. UU. antes de enviar** (A2P 10DLC para un
   número local, o la verificación *toll-free* para uno 800/888). Sin ese
   registro las operadoras bloquean los mensajes. La aprobación tarda de
   días a semanas, así que conviene empezarlo cuanto antes. El sitio ya trae
   lo que suelen pedir: el aviso de SMS y el enlace a *Text Message Terms*
   junto a la casilla de consentimiento (`public/legal.html#messages`).
3. En Render, definir `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` y
   `TWILIO_FROM_NUMBER` (el número de envío, con `+1`; la idea es usar el del restaurante, ver `MENSAJES.md`).
4. Los teléfonos que escriben los clientes (`(518) 302-5235`) se convierten
   solos al formato internacional que exige Twilio (`+15183025235`).

**Probar:** con las variables ya puestas, hacer una reservación desde el sitio
con un teléfono propio. Debe llegar el SMS en un minuto. Si no llega,
Render → Logs: buscar `ENVIADO` (salió) o `ERROR SMS` (con el motivo).

---

## 3. Despliegue en Render

Configuración del servicio (Render → Settings):

- **Start Command:** `python3 server.py`
- **Build Command:** vacío (no hay nada que instalar).
- **Health Check Path:** `/healthz`. Con esto Render no da por bueno un
  despliegue que arranca roto, y reinicia el servicio si deja de responder.
- **Auto-Deploy:** `After CI checks pass`. Así un cambio que rompa las pruebas
  no llega al sitio en vivo.

**Una sola instancia.** La protección contra el sobrecupo vive dentro del
proceso del servidor. Mientras Render corra una instancia (lo normal, y lo
único posible en los planes básicos) es suficiente; si algún día se escala a
varias, primero hay que mover esa comprobación a la base de datos.

**Plan de pago (recomendado, unos 7 USD al mes).** El plan gratuito duerme el
servicio tras 15 minutos sin visitas y el siguiente cliente espera ~50
segundos. El monitor de la sección 4 lo mantiene despierto en la práctica, pero
el plan de pago es la solución de verdad: sin esperas, sin límite de horas y
con soporte.

---

## 4. Monitoreo gratuito (UptimeRobot)

1. Crear cuenta en <https://uptimerobot.com> (plan gratuito).
2. *New monitor* → tipo **HTTP(s)**.
3. URL: `https://www.whitebearrestaurant.com/healthz`
   (o el dominio propio cuando lo haya).
4. Intervalo: **5 minutos**.
5. Alertas: el correo y, si se quiere, el teléfono del dueño.

Además de avisar cuando el sitio se cae, este monitor:

- mantiene despierto el servicio de Render en el plan gratuito, y
- evita que Supabase pause el proyecto: en el plan gratuito, Supabase pausa
  los proyectos que pasan 7 días sin actividad, y `/healthz` hace una consulta
  real a la base cada vez.

---

## 5. Respaldos

### Automático, cada noche (GitHub Actions)

El flujo `.github/workflows/backup.yml` exporta todos los datos cada noche, los
**cifra** y los guarda 90 días en GitHub. Para activarlo, en GitHub →
Settings → Secrets and variables → Actions → *New repository secret*, crear:

- `SUPABASE_URL` y `SUPABASE_KEY`: los mismos valores que en Render.
- `BACKUP_PASSPHRASE`: una frase larga inventada. **Guárdala en un gestor de
  contraseñas**: sin ella los respaldos no se pueden abrir.

Para probarlo sin esperar a la noche: Actions → *Respaldo diario* → *Run
workflow*.

**Para recuperar un respaldo:** Actions → *Respaldo diario* → la ejecución
del día que se quiera → *Artifacts* → descargar. Dentro hay un
`respaldo.json.enc`. Se descifra con:

```bash
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -in respaldo.json.enc -out respaldo.json
```

(pide la `BACKUP_PASSPHRASE`).

> **Ojo:** GitHub desactiva los flujos programados de un repositorio que pasa
> 60 días sin cambios, y avisa por correo. Si llega ese correo, entrar a
> Actions → *Respaldo diario* → *Enable workflow*.

### Manual

```bash
SUPABASE_URL=... SUPABASE_KEY=... python3 scripts/backup.py
```

Deja el archivo en `backups/` (que no se sube a git: contiene teléfonos de
clientes).

### Restaurar

```bash
SUPABASE_URL=... SUPABASE_KEY=... python3 scripts/restore.py respaldo.json
```

Pide confirmación. Escribe cada fila del respaldo encima de la actual con el
mismo id y **no borra nada** de lo que haya de más, así que es seguro
ejecutarlo sobre una base que solo perdió una parte.

**Qué no entra en el respaldo:** las fotos que suben los clientes con sus
reseñas. Viven en Supabase Storage (bucket `review-photos`) y el respaldo solo
guarda su URL. Si se quiere copia de esas imágenes, descargarlas desde el panel
de Supabase de vez en cuando.

**Una vez cada tres meses, probar una restauración** sobre una copia local
(sin `SUPABASE_URL`, va a `data/`). Un respaldo que nunca se ha restaurado no
se sabe si sirve.

---

## 6. Limpieza de datos viejos

El servidor borra una vez al día las reservaciones con fecha anterior a
`RESERVATION_RETENTION_DAYS` días. Sin definirla son **60 días (2 meses)**, que
es lo que promete la política de privacidad. Definida vacía, no se borra nada.

Conviene activarlo por dos motivos: la base no crece sin fin (la tablet
descarga la lista entera en cada actualización), y no guardar teléfonos y
correos de clientes más tiempo del necesario. **El número debe coincidir con
lo que diga la política de privacidad del sitio.** Por seguridad, el servidor
se niega a usar menos de 30 días.

Las reseñas y las fotos de la galería no se borran nunca solas.

---

## 7. Dominio propio

**Estado (2026-10-05):** el dominio es `whitebearrestaurant.com`, comprado en
Cloudflare. La dirección principal es `https://www.whitebearrestaurant.com`;
la versión sin `www` redirige a ella (lo hace Render). La dirección
`whitebearrestaurantreservation.onrender.com` sigue funcionando.

**DNS (en Cloudflare, con el proxy apagado: "DNS only", nube gris):**

| Tipo | Nombre | Valor |
|---|---|---|
| A | `@` | `216.24.57.1` (la IP que indica Render) |
| CNAME | `www` | `whitebearrestaurantreservation.onrender.com` |

Con la nube naranja (proxy de Cloudflare) el certificado HTTPS de Render
puede fallar al renovarse: déjala gris.

**Si algún día hay que repetirlo o cambiar de dominio:**
1. Comprar el dominio (unos 12 USD al año; Cloudflare Registrar o Namecheap).
   **Activar la renovación automática**: un dominio caducado lo puede comprar
   otro.
2. Render → el servicio → Settings → Custom Domains → añadir el dominio (y su
   versión con `www`), crear en el DNS los registros que indique y tocar las
   flechas circulares hasta que ambos digan *Verified* y *Certificate Issued*.
   Render pone el certificado HTTPS solo.
3. Cambiar `PUBLIC_BASE_URL` en Render por la dirección principal (los enlaces
   de los SMS la usan).
4. Actualizar el `canonical`, las etiquetas `og:` y el JSON-LD de
   `public/index.html`, el de `public/legal.html`, `public/sitemap.xml` y
   `public/robots.txt`.
5. Cambiar la URL del monitor de UptimeRobot.

---

## 8. Si algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| UptimeRobot avisa "Down" y el sitio no carga | Render caído o el servicio no arranca | Render → Logs. Si el último despliegue lo rompió: Render → Events → *Rollback* al anterior. |
| `/healthz` responde 503 con `"storage": "error"` | El servidor no puede usar Supabase | **El campo `"problem"` de esa misma página dice el motivo** (sin mostrar ninguna clave). Casos típicos: *"tiene un espacio o un salto de línea"* o *"un caracter no válido"* (la variable se pegó mal: volver a copiarla en Render → Environment); *"debe empezar con https://"* (corregir `SUPABASE_URL`); *"rechazó la clave"* (`SUPABASE_KEY` debe ser la `service_role`); *"no se pudo conectar"* (mirar <https://status.supabase.com> y que el proyecto no esté **pausado**: botón *Restore*). |
| `/healthz` responde 503 con `"storage": "local"` | En Render faltan `SUPABASE_URL` y/o `SUPABASE_KEY` | Las reservaciones se estarían guardando en un disco que se borra al reiniciar. Añadir las dos variables en Render → Environment cuanto antes. El arranque también lo escribe en Logs entre líneas de `!!`. |
| La tablet no muestra reservaciones nuevas | La tablet perdió la conexión o el servicio se reinició | Recargar la página de la tablet. Si sigue igual, mirar `/healthz`. |
| Los clientes no reciben SMS | Credenciales sin configurar, caducadas o sin saldo | Render → Logs, buscar `ERROR SMS`. Revisar el saldo de Twilio y el registro del número. |
| Los recordatorios salen a la hora equivocada | Zona horaria | `/healthz` muestra la hora que cree el servidor. Si no es la de Lake Placid, revisar `RESTAURANT_TIMEZONE`. |
| "Error interno" al reservar | Un fallo de código o de Supabase | Render → Logs, buscar `[ERROR] POST /api/reservations`. Con ese texto cualquier programador sabe por dónde empezar. |
| El formulario de reservas sale gris con un aviso rojo | Alguien apagó las reservaciones desde el panel | Panel → botón *Reservaciones apagadas* (barra de arriba) → confirmar. |
| El panel o el sitio se ven rotos justo después de actualizar (sin mesas, botones muertos) | El navegador usó un .js o .css viejo guardado en caché | Ya no debería pasar: el servidor versiona los archivos (`?v=`) y los revalida. Si ocurriera, abrir la página desde la dirección con `www` o borrar los datos del sitio en Safari (Ajustes → Safari → Avanzado → Datos de sitios web). |
| Se borraron datos por error | — | Restaurar el respaldo más reciente (sección 5). |
| Una actualización de Python en Render rompió algo | Render cambió la versión por defecto | Fijar la versión que funcionaba con la variable `PYTHON_VERSION` en Render (por ejemplo `3.13.5`). |

---

## 9. Calendario de mantenimiento

**Cada mes** (5 minutos)
- Abrir `/healthz` y comprobar `"ok": true` y la hora.
- Mirar que el último *Respaldo diario* en GitHub Actions esté en verde.
- Revisar las reseñas retenidas, si las hay.

**Cada tres meses**
- Probar una restauración (sección 5).
- Mirar los logs de Render buscando `[ERROR]`.

**Cada año**
- Confirmar la renovación del dominio y el método de pago de Render.
- Cambiar `ADMIN_PASSWORD` y `STAFF_PASSWORD` (y siempre que alguien con
  acceso deje de trabajar en el restaurante).
- Revisar que las pruebas pasen con la versión de Python más reciente (el flujo
  `tests.yml` lo hace en cada cambio).

---

## 10. Pruebas

```bash
python3 -m unittest discover -s tests -v
```

No hace falta instalar nada. Las pruebas levantan su propio servidor con datos
en una carpeta temporal: nunca tocan Supabase ni los datos reales. GitHub las
ejecuta en cada cambio (`.github/workflows/tests.yml`), con la versión más
antigua y la más nueva de Python que usamos.

Antes de subir un cambio, ejecutarlas. Si una falla, el cambio rompió algo que
antes funcionaba.

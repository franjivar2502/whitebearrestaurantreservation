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

El sitio siempre está en línea y se aceptan reservaciones a cualquier hora
(24/7); ya no hay pestaña "Sitio web" ni modo "cerrado temporalmente".

---

## 2. Variables de entorno (Render → el servicio → Environment)

| Variable | Obligatoria | Para qué |
|---|---|---|
| `SUPABASE_URL` | Sí | URL del proyecto de Supabase (`https://xxxx.supabase.co`). Sin ella los datos se pierden en cada reinicio. |
| `SUPABASE_KEY` | Sí | Clave `service_role` de Supabase. **Secreta.** |
| `ADMIN_PASSWORD` | Sí | Contraseña del panel de fotos (`/admin-photos.html`). |
| `STAFF_PASSWORD` | Sí, cuando se active el acceso del personal | Contraseña de la tablet. |
| `PUBLIC_BASE_URL` | Sí | La dirección pública del sitio, para los enlaces de los SMS y correos. Cámbiala al estrenar dominio propio. |
| `RESTAURANT_TIMEZONE` | No | Zona horaria del restaurante. Por defecto `America/New_York`. |
| `RESERVATION_RETENTION_DAYS` | No | Días que se guardan las reservaciones pasadas (60 si no se define). Ver sección 6. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Para correos reales | Ver `notifications.py`. Sin ellas los correos solo se simulan. |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` | Para SMS reales | Sin ellas los SMS solo se simulan. |

Nunca escribas ninguno de estos valores en el repositorio: es público.

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
3. URL: `https://whitebearrestaurantreservation.onrender.com/healthz`
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

1. Comprar el dominio (unos 12 USD al año; Cloudflare Registrar o Namecheap).
   **Activar la renovación automática**: un dominio caducado lo puede comprar
   otro.
2. Render → el servicio → Settings → Custom Domains → añadir el dominio y
   seguir las instrucciones de DNS. Render pone el certificado HTTPS solo.
3. Cambiar `PUBLIC_BASE_URL` en Render.
4. Actualizar el `canonical`, las etiquetas `og:` y el JSON-LD de
   `public/index.html`, y `public/sitemap.xml`.
5. Cambiar la URL del monitor de UptimeRobot.

---

## 8. Si algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| UptimeRobot avisa "Down" y el sitio no carga | Render caído o el servicio no arranca | Render → Logs. Si el último despliegue lo rompió: Render → Events → *Rollback* al anterior. |
| `/healthz` responde 503 con `"storage": "error"` | Supabase no responde | <https://status.supabase.com>. En el panel de Supabase, mirar si el proyecto está **pausado** (botón *Restore*). Revisar que `SUPABASE_KEY` no haya cambiado. |
| La tablet no muestra reservaciones nuevas | La tablet perdió la conexión o el servicio se reinició | Recargar la página de la tablet. Si sigue igual, mirar `/healthz`. |
| Los clientes no reciben SMS ni correos | Credenciales sin configurar, caducadas o sin saldo | Render → Logs, buscar `ERROR SMS` o `ERROR EMAIL`. Revisar saldo de Twilio y la contraseña de aplicación del correo. |
| Los recordatorios salen a la hora equivocada | Zona horaria | `/healthz` muestra la hora que cree el servidor. Si no es la de Lake Placid, revisar `RESTAURANT_TIMEZONE`. |
| "Error interno" al reservar | Un fallo de código o de Supabase | Render → Logs, buscar `[ERROR] POST /api/reservations`. Con ese texto cualquier programador sabe por dónde empezar. |
| El formulario de reservas sale gris con un aviso rojo | Alguien apagó las reservaciones desde el panel | Panel → botón *Reservaciones apagadas* (barra de arriba) → confirmar. |
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

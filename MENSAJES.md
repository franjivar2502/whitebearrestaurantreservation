# Activar los mensajes de confirmación (SMS y correo)

El sistema ya envía tres mensajes por reservación; solo faltan las
credenciales. Mientras no estén puestas, los mensajes se **simulan** (se
escriben en Render → Logs como `DRY-RUN`) y no sale nada.

| Cuándo | Mensaje |
|---|---|
| Al reservar | Confirmación de recibida, con el código |
| El día anterior (o 30 min antes si es del mismo día) | Enlace para confirmar asistencia |
| 15 minutos antes | Aviso de mesa lista |

Cada mensaje sale en el idioma con que el cliente llenó el formulario
(inglés, español o francés). Va por **SMS** si hay teléfono y por **correo** si
dejó su email.

**Orden recomendado:** primero el correo (queda listo el mismo día), y en
paralelo empezar el registro de SMS, que es lo que tarda.

---

## 1. Correo (SMTP)

Nunca escribas estas claves en el repositorio ni en el chat: solo en Render →
el servicio → **Environment**.

### Opción rápida: una cuenta de Gmail (10 minutos)

1. Usa una cuenta de Gmail del restaurante (mejor que una personal) y activa
   la **verificación en dos pasos** en myaccount.google.com → Seguridad.
2. En myaccount.google.com busca **Contraseñas de aplicación**, crea una
   llamada "White Bear" y copia las 16 letras que te da.
3. En Render añade estas variables:

| Variable | Valor |
|---|---|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | la dirección de Gmail |
| `SMTP_PASSWORD` | la contraseña de aplicación de 16 letras, **sin espacios** |
| `SMTP_FROM` | (opcional) la dirección que verá el cliente; si falta usa `SMTP_USER` |

Los correos saldrán desde esa dirección de Gmail. Gmail limita el envío diario,
suficiente para un restaurante.

### Opción profesional: enviar desde `reservas@whitebearrestaurant.com`

Usa un servicio de correo transaccional (Resend, Postmark, SendGrid, Brevo...).
Te da un servidor SMTP y te pide añadir en Cloudflare unos registros **SPF/DKIM**
para tu dominio; sin ellos los correos caen en spam. Las mismas cinco variables
de arriba, con los datos que te dé el servicio.

---

## 2. SMS (Twilio)

1. Crea la cuenta en twilio.com y completa la verificación de identidad.
2. Compra un número de EE. UU. Dos caminos (revisa las condiciones y los
   precios vigentes en Twilio antes de elegir):
   - **Toll-free (800/833/844/855/866/877/888):** suele ser más sencillo para un
     negocio pequeño; se pide una *verificación toll-free*.
   - **Número local (518):** se ve más cercano, pero exige registrar la marca y
     la campaña (**A2P 10DLC**).
3. **Registra el envío antes de usarlo.** En EE. UU., las operadoras bloquean
   los SMS de números sin registrar. La aprobación tarda de **días a semanas**.
   Los textos para pegar están en la sección 3.
4. Cuando Twilio apruebe, en Render añade:

| Variable | Valor |
|---|---|
| `TWILIO_ACCOUNT_SID` | empieza con `AC` (Twilio → Console) |
| `TWILIO_AUTH_TOKEN` | el token secreto (Twilio → Console). **No lo compartas.** |
| `TWILIO_FROM_NUMBER` | el número comprado, con `+1`, por ejemplo `+15185550123` |

Los teléfonos que escriben los clientes (`(518) 302-5235`) se convierten solos al
formato internacional que exige Twilio.

---

## 3. Textos para el registro de Twilio (copiar y pegar)

**Datos del negocio**

- Nombre: White Bear Restaurant
- Dirección: 2793 Wilmington Rd, Lake Placid, NY 12946
- Teléfono: (518) 302-5235
- Sitio web: https://www.whitebearrestaurant.com
- Tipo de negocio: restaurante (hospitalidad). Los datos fiscales (EIN o, si es
  persona física, SSN/propietario único) los pone el dueño en el formulario de
  Twilio.

**Caso de uso:** Account notifications / Customer care (mensajes sobre una
reservación que el propio cliente hizo; **no es marketing**).

**Descripción de la campaña**

> White Bear Restaurant sends transactional text messages to guests who book a
> table on our website. Each reservation triggers up to three messages: a booking
> confirmation, a request to confirm attendance, and a short alert about 15
> minutes before the table is ready. Messages are informational only. We never
> send promotions, and we never share phone numbers with third parties.

**Cómo da su consentimiento el cliente (opt-in)**

> Guests enter their mobile number in the reservation form at
> https://www.whitebearrestaurant.com and must check a box agreeing to the
> Reservation Terms and Privacy Policy. Right under the box, the form states:
> "By booking, you agree to receive automated texts about this reservation at the
> number above (usually up to 3: confirmation, attendance check and table-ready
> alert). Not marketing. Msg & data rates may apply. Reply STOP to opt out, HELP
> for help." and links to the Text Message Terms
> (https://www.whitebearrestaurant.com/legal.html#messages). Without the box
> checked, the reservation cannot be submitted.

**Enlaces que suelen pedir**

- Política de privacidad: https://www.whitebearrestaurant.com/legal.html#privacy
- Términos de los mensajes: https://www.whitebearrestaurant.com/legal.html#messages
- Captura del formulario con la casilla y el aviso: abrir el sitio, bajar a
  "Reserve your table" y capturar la parte de la casilla de consentimiento.

**Mensajes de ejemplo** (los tres que envía el sistema, tal cual)

1. `White Bear Restaurant: Hi Maria, we received your reservation for Monday, Oct 12 at 7:00 PM (party of 4). Code #a1b2c3d4. See you soon! Reply STOP to opt out of texts.`
2. `White Bear Restaurant: Hi Maria, please confirm you're coming on Monday, Oct 12 at 7:00 PM (party of 4): https://www.whitebearrestaurant.com/confirm.html?id=a1b2c3d4e5f60718&lang=en If you can't confirm, please call (518) 302-5235.`
3. `White Bear Restaurant: Hi Maria, your table for 4 will be ready in 15 minutes (at 7:00 PM). See you soon!`

**Frecuencia:** hasta 3 mensajes por reservación.
**Palabras de baja y ayuda:** STOP y HELP (Twilio las atiende por su cuenta).
**Volumen estimado:** el que corresponda al restaurante; para un negocio de este
tamaño suele caber en la categoría de volumen bajo.

---

## 4. Variable pendiente de Render: `PUBLIC_BASE_URL`

Valor: `https://www.whitebearrestaurant.com`. Los enlaces de confirmación de
asistencia la usan; sin ella apuntarían a una dirección de prueba.

---

## 5. Probar

1. Con las variables ya puestas (Render se reinicia solo al guardar), haz una
   reservación en https://www.whitebearrestaurant.com con tu propio teléfono y
   correo.
2. En un minuto deben llegar el SMS y el correo.
3. Si no llega, Render → **Logs**: busca `ENVIADO` (salió) o `ERROR SMS` /
   `ERROR EMAIL` (con el motivo exacto).
4. Cancela o borra la reservación de prueba desde el panel del staff.

| Síntoma en Logs | Causa probable |
|---|---|
| `DRY-RUN SMS` / `DRY-RUN EMAIL` | Faltan variables en Render (o el servicio no se reinició) |
| `ERROR SMS ... 21211` / "invalid 'To'" | Número del cliente no válido |
| `ERROR SMS ... 30034` / "unregistered" | El número aún no tiene el registro de EE. UU. aprobado |
| `ERROR EMAIL ... 535` | Contraseña de aplicación incorrecta (copiarla de nuevo, sin espacios) |

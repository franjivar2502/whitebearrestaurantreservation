# Activar los mensajes de confirmación (solo SMS)

El sistema ya envía tres mensajes por reservación; solo faltan las
credenciales. Mientras no estén puestas, los mensajes se **simulan** (se
escriben en Render → Logs como `DRY-RUN`) y no sale nada. **No se envía correo:**
todo va por SMS al teléfono que el cliente escribe en el formulario.

| Cuándo | Mensaje |
|---|---|
| Al reservar | Confirmación de recibida, con el código |
| El día anterior (o 30 min antes si es del mismo día) | Enlace para confirmar asistencia |
| 15 minutos antes | Aviso de mesa lista |

Cada mensaje sale en el idioma con que el cliente llenó el formulario
(inglés, español o francés).

Nunca escribas las claves en el repositorio ni en el chat: solo en Render → el
servicio → **Environment**.

---

## 1. Usar el número que ya tiene el restaurante: (518) 302-5235

Los SMS salen por Twilio y necesitan un número "de envío". Lo ideal es que sea
el que los clientes ya conocen. Qué se puede hacer depende del **tipo de línea**
(pregúntale a quien te da el servicio: ¿es fija, VoIP o celular?). Confirma las
condiciones vigentes en la consola de Twilio antes de decidir:

1. **Línea fija o VoIP:** Twilio permite habilitar mensajes de texto en un
   número que ya existe (*Hosted SMS*) sin quitarle las llamadas, o **portarlo**
   a Twilio. Es la opción para que el cliente vea (518) 302-5235.
2. **Celular:** normalmente no se puede usar tal cual para envío automático.
3. **Mientras tanto / si no se puede:** compra un número nuevo en Twilio (el
   toll-free suele registrarse más rápido). El mensaje ya incluye "llama al
   (518) 302-5235", así que el cliente sigue viendo el número del restaurante.

Sea cual sea, el número final se pone en Render como `TWILIO_FROM_NUMBER`, con
formato `+15183025235`.

---

## 2. SMS (Twilio)

1. Crea la cuenta en twilio.com y completa la verificación de identidad.
2. Habilita el número (sección 1). En EE. UU. hay dos tipos de registro (revisa
   precios y condiciones vigentes en Twilio):
   - **Número local (518) o Hosted SMS:** registrar la marca y la campaña
     (**A2P 10DLC**).
   - **Toll-free:** *verificación toll-free*, suele ser más sencilla.
3. **Registra el envío antes de usarlo.** En EE. UU., las operadoras bloquean
   los SMS de números sin registrar. La aprobación tarda de **días a semanas**.
   Los textos para pegar están en la sección 3.
4. Cuando Twilio apruebe, en Render añade:

| Variable | Valor |
|---|---|
| `TWILIO_ACCOUNT_SID` | empieza con `AC` (Twilio → Console) |
| `TWILIO_AUTH_TOKEN` | el token secreto (Twilio → Console). **No lo compartas.** |
| `TWILIO_FROM_NUMBER` | el número de envío, con `+1`, por ejemplo `+15183025235` |

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
   reservación en https://www.whitebearrestaurant.com con tu propio teléfono.
2. En un minuto debe llegar el SMS.
3. Si no llega, Render → **Logs**: busca `ENVIADO` (salió) o `ERROR SMS` (con el motivo exacto).
4. Cancela o borra la reservación de prueba desde el panel del staff.

| Síntoma en Logs | Causa probable |
|---|---|
| `DRY-RUN SMS` | Faltan variables en Render (o el servicio no se reinició) |
| `ERROR SMS ... 21211` / "invalid 'To'" | Número del cliente no válido |
| `ERROR SMS ... 30034` / "unregistered" | El número aún no tiene el registro de EE. UU. aprobado |

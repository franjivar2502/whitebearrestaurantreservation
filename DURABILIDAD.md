# Por qué este sistema puede seguir funcionando en 2036

Documento para la conversación con el cliente. No es una promesa comercial:
es la lista de las decisiones técnicas que hacen que un proyecto sobreviva una
década, y de las que todavía faltan.

---

## Lo que ya juega a favor

### 1. Cero dependencias

El servidor entero corre con la biblioteca estándar de Python. No hay
`requirements.txt`, no hay `node_modules`, no hay paso de compilación.

Esto es lo más importante de toda la lista. **La causa número uno de que un
proyecto web muera no es que el servidor se apague: es que nadie puede volver
a construirlo.** Un sitio típico de 2016 hecho con Node arrastraba 900
paquetes; hoy no compila, y arreglarlo cuesta más que rehacerlo. Aquí no hay
nada que se pueda pudrir: dentro de diez años se clona el repositorio, se
ejecuta `python3 server.py` y arranca.

El frontend es igual: HTML, CSS y JavaScript sin framework. No hay React que
actualizar, ni versión mayor que rompa la anterior.

### 2. Los datos no están atrapados

Supabase es Postgres. Si Supabase cierra o sube el precio, los datos salen con
un `pg_dump` y entran en cualquier otro Postgres del mundo. No hay formato
propietario.

Además el sistema **ya sabe funcionar sin Supabase**: si las variables de
entorno no están, guarda en archivos JSON locales. Esa ruta de escape está
escrita y probada, no es teoría.

### 3. Nada depende de un servicio ajeno para verse bien

Las fotos de los platos, el logo y la imagen para compartir están en el
repositorio. La única excepción es la foto de la galería, que todavía apunta a
una URL de Google (ver pendientes).

Las tipografías vienen de Google Fonts, pero el CSS declara alternativas
reales: si Google Fonts desaparece, el sitio se ve con Georgia y la sans del
sistema, no roto.

### 4. El fondo 3D no arrastra 600 KB

El shader de WebGL está escrito a mano. La alternativa habitual —Three.js—
pesa unos 600 KB y cambia de API cada pocos años. Esto son 4 KB que no se
actualizan nunca.

---

## Lo que hay que resolver para que la década se cumpla

Ordenado por lo que más rápido mata un proyecto.

### 1. El plan gratuito de Render duerme el servicio

Es el riesgo más inmediato y el único que ya está haciendo daño: el arranque
en frío tarda unos 50 segundos. Un cliente que entra desde Google se va antes.
Googlebot también abandona, así que además frena la indexación.

**Qué cuesta:** el plan de pago de Render ronda los 7 dólares al mes. Es la
mejor relación coste/beneficio de toda esta lista.

### 2. Dominio propio

Hoy la dirección es `whitebearrestaurantreservation.onrender.com`. Dos
problemas: depende del nombre de un proveedor concreto, y si algún día se
migra a otro hosting, todos los enlaces compartidos mueren.

Con un dominio propio (`whitebearrestaurant.com`, unos 12 dólares al año), el
hosting se puede cambiar cuantas veces haga falta sin que nadie se entere.
**Esto es lo que hace que la década sea posible:** el dominio es el activo, el
hosting es intercambiable.

Hay que acordarse de actualizar entonces el `canonical`, el `sitemap.xml`, los
`og:` y la URL dentro del JSON-LD.

### 3. Copias de seguridad automáticas

Hoy la copia es manual (la que se hizo el 1 de octubre). Supabase tiene copias
en su plan de pago; aparte conviene un volcado periódico a otro sitio.

Regla sencilla: **un dato que existe en un solo lugar es un dato que ya se
perdió, solo que todavía no lo sabes.**

### 4. Las credenciales

- `ADMIN_PASSWORD` sigue siendo la de prueba, y el valor está escrito en el
  README de un repositorio **público**. Cualquiera puede leerlo y entrar al
  panel de fotos del sitio en vivo. Es lo primero que hay que cerrar.
- Faltan las credenciales reales de Twilio y SMTP: hoy los avisos por SMS y
  correo corren en modo simulado, no se envía nada.

### 5. Quién mantiene esto

La pregunta que el cliente va a hacer, y conviene llevar la respuesta
preparada. Opciones honestas:

- **Mantenimiento por horas, a demanda.** Lo normal en un negocio de este
  tamaño: el restaurante llama cuando quiere un cambio.
- **Una cuota mensual** que cubra hosting, dominio, copias y un número de
  horas. Da ingresos recurrentes y le quita al cliente la gestión.
- **Entrega llave en mano.** Se le entrega el repositorio y las cuentas. Es
  viable justamente porque no hay dependencias: otro programador puede
  retomarlo sin arqueología.

El README y este documento están escritos para que la tercera opción sea real
y no una excusa.

---

## Sobre las reseñas negativas

Antes, cualquier reseña con una palabra negativa se descartaba y nadie la veía.
Ya no: ahora **no se publica automáticamente pero sí llega al panel**
(`/admin-photos.html`, sección "Reseñas de clientes"), donde el staff decide si
la publica o la oculta, y puede responder o llamar al cliente. Ocultar no
borra: la reseña queda guardada.

Por qué el cambio, para explicárselo al cliente:

1. **En Estados Unidos hay norma al respecto.** Desde 2024 la FTC regula la
   supresión de reseñas negativas cuando eso da una imagen engañosa del
   negocio (16 CFR Parte 465). Un muro donde solo hay cincos no es creíble, y
   además puede acarrear problemas. Conviene que el staff publique las
   críticas legítimas y oculte solo lo ofensivo, falso o spam.
2. **La calificación no decide nada.** Una reseña de una estrella sin palabras
   de la lista se publica igual que una de cinco; no se filtra por nota.
3. **Por eso no se declaró la calificación en los datos estructurados.** La
   nota de 4.2 venía de Google, no de las reseñas de la página; publicarla
   como propia incumple las normas de Google sobre reseñas.

---

## Resumen para el cliente, en una frase

El sistema está construido sin dependencias que caduquen y con los datos en un
formato estándar, así que lo que determina si sigue vivo en diez años no es la
tecnología: son **siete dólares al mes de hosting, doce al año de dominio, y
alguien que lo atienda cuando el restaurante lo necesite.**

/*
 * Traducción del panel de tablet (staff): inglés por defecto, con
 * español y serbio (alfabeto latino) como opciones. Independiente del
 * i18n.js del sitio de clientes (que usa inglés/español/francés) —
 * tienen públicos distintos, así que cada uno guarda su propio idioma
 * (clave de localStorage separada) y no se pisan entre sí.
 */
(function (global) {
  const STORAGE_KEY = "wb-tablet-lang";
  const DEFAULT_LANG = "en";
  const SUPPORTED = ["en", "es", "sr"];

  const LOCALE_MAP = { en: "en-US", es: "es-ES", sr: "sr-Latn-RS" };
  const TIME_STYLE = { en: "12h-en", es: "12h-es", sr: "24h" };

  const DICTIONARIES = {
    en: {
      pageTitle: "White Bear Restaurant — Reservations Panel",
      header: { reservations: "reservations", guests: "guests", refresh: "Refresh now" },
      views: { reservations: "Reservations", tables: "Tables" },
      tables: {
        summary: "{available} of {total} seats free right now",
        square4: "Square tables (4)",
        rect4: "Rectangular tables (4)",
        rect6: "Rectangular tables (6)",
        rect12: "Rectangular table (12)",
        rect10: "Rectangular table (10)",
        table: "Table {n}",
        seats: "{n} seats",
        room_left: "Front room — bar & entrance",
        room_right: "Back room",
        bar: "Bar",
        entrance: "Entrance",
        bathroom: "Bathroom",
        available: "Available",
        unavailable: "Unavailable",
        hint: "Tap a table on the plan to take it out of service (private event, broken chair, etc.). This lowers the seats the customer site can book.",
      },
      booking: {
        on: "Reservations on",
        off: "Reservations off",
        banner: "Online reservations are off. The customer site isn't taking new bookings.",
        confirmOff:
          "Turn off online reservations? The customer site will stop taking new bookings until you turn them back on. Reservations already booked are not affected, and you can still add one here by phone.",
        confirmOn: "Turn online reservations back on?",
        turnedOff: "Online reservations are off.",
        turnedOn: "Online reservations are on.",
        failed: "Couldn't change it. Check the connection.",
      },
      tabs: {
        today: "Today",
        upcoming: "Upcoming",
        all: "All",
        pending: "Pending",
        confirmed: "Confirmed",
        active: "Unfinished",
        needsCall: "Needs confirmation",
      },
      login: {
        title: "Staff access",
        hint: "Enter the staff password to see reservations.",
        password: "Password",
        submit: "Sign in",
        wrong: "Wrong password.",
        failed: "Couldn't reach the server. Try again.",
        tooMany: "Too many wrong attempts. Wait 15 minutes and try again.",
      },
      newRes: {
        open: "New reservation",
        title: "New reservation",
        name: "Name",
        phone: "Phone",
        date: "Date",
        time: "Time",
        partySize: "Guests",
        seating: "Seating",
        seatingNone: "No preference",
        seatingInside: "Inside",
        seatingOutside: "Outside",
        notes: "Notes",
        cancel: "Cancel",
        save: "Save",
        added: "Reservation added for {name}",
        failed: "Couldn't save the reservation. Check the connection.",
      },
      errors: {
        NAME_REQUIRED: "Enter a name (2 to 120 characters).",
        PHONE_INVALID: "Enter a valid phone number.",
        EMAIL_INVALID: "That email doesn't look valid.",
        DATE_INVALID: "That date isn't valid.",
        DATE_PAST: "The date can't be in the past.",
        DATE_TOO_FAR: "Up to 6 months ahead only.",
        TIME_INVALID: "That time isn't valid.",
        BOOKING_CLOSED: "Online reservations are off.",
        PARTY_SIZE_INVALID: "Enter the number of guests.",
        PARTY_SIZE_OUT_OF_RANGE: "Between 1 and 40 guests. For more, split the booking.",
        NO_AVAILABILITY: "Not enough seats free at that time.",
        NOTES_TOO_LONG: "The note is too long.",
        PREORDER_INVALID: "The pre-order isn't valid.",
      },
      emptyState: "No reservations to show.",
      today: "Today",
      status: {
        pending: "Pending",
        confirmed: "Confirmed",
        seated: "Seated",
        completed: "Completed",
        cancelled: "Cancelled",
      },
      actions: { confirm: "Confirm", seat: "Seat", complete: "Complete", cancel: "Cancel" },
      attendance: {
        confirmed: "Attendance confirmed by the guest",
        waiting: "Waiting for confirmation — call if they don't respond",
      },
      toast: {
        newReservation: "New reservation: {name}",
        newReservations: "{count} new reservations",
        updateFailed: "Couldn't update the reservation.",
      },
    },
    es: {
      pageTitle: "White Bear Restaurant — Panel de Reservaciones",
      header: { reservations: "reservaciones", guests: "comensales", refresh: "Actualizar ahora" },
      views: { reservations: "Reservaciones", tables: "Mesas" },
      tables: {
        summary: "{available} de {total} asientos libres ahora mismo",
        square4: "Mesas cuadradas (4)",
        rect4: "Mesas rectangulares (4)",
        rect6: "Mesas rectangulares (6)",
        rect12: "Mesa rectangular (12)",
        rect10: "Mesa rectangular (10)",
        table: "Mesa {n}",
        seats: "{n} pers.",
        room_left: "Salón de la entrada — barra",
        room_right: "Salón del fondo",
        bar: "Barra",
        entrance: "Entrada",
        bathroom: "Baño",
        available: "Disponible",
        unavailable: "No disponible",
        hint: "Toca una mesa en el plano para sacarla de servicio (evento privado, silla rota, etc.). Esto reduce los asientos que el sitio de clientes puede reservar.",
      },
      booking: {
        on: "Reservaciones activas",
        off: "Reservaciones apagadas",
        banner: "Las reservaciones están apagadas. El sitio de clientes no está aceptando nuevas.",
        confirmOff:
          "¿Apagar las reservaciones en línea? El sitio de clientes dejará de aceptar nuevas hasta que las vuelvas a encender. Las reservaciones ya tomadas no se tocan, y desde aquí puedes seguir apuntando las que entren por teléfono.",
        confirmOn: "¿Volver a encender las reservaciones en línea?",
        turnedOff: "Reservaciones en línea apagadas.",
        turnedOn: "Reservaciones en línea encendidas.",
        failed: "No se pudo cambiar. Revisa la conexión.",
      },
      tabs: {
        today: "Hoy",
        upcoming: "Próximas",
        all: "Todas",
        pending: "Pendientes",
        confirmed: "Confirmadas",
        active: "Sin finalizar",
        needsCall: "Por confirmar",
      },
      login: {
        title: "Acceso del personal",
        hint: "Escribe la contraseña del personal para ver las reservaciones.",
        password: "Contraseña",
        submit: "Entrar",
        wrong: "Contraseña incorrecta.",
        failed: "No se pudo conectar con el servidor. Inténtalo de nuevo.",
        tooMany: "Demasiados intentos fallidos. Espera 15 minutos y vuelve a intentarlo.",
      },
      newRes: {
        open: "Nueva reservación",
        title: "Nueva reservación",
        name: "Nombre",
        phone: "Teléfono",
        date: "Fecha",
        time: "Hora",
        partySize: "Personas",
        seating: "Ubicación",
        seatingNone: "Sin preferencia",
        seatingInside: "Adentro",
        seatingOutside: "Afuera",
        notes: "Notas",
        cancel: "Cancelar",
        save: "Guardar",
        added: "Reservación agregada para {name}",
        failed: "No se pudo guardar. Revisa la conexión.",
      },
      errors: {
        NAME_REQUIRED: "Escribe un nombre (de 2 a 120 caracteres).",
        PHONE_INVALID: "Escribe un teléfono válido.",
        EMAIL_INVALID: "Ese correo no parece válido.",
        DATE_INVALID: "Esa fecha no es válida.",
        DATE_PAST: "La fecha no puede ser en el pasado.",
        DATE_TOO_FAR: "Solo hasta 6 meses de anticipación.",
        TIME_INVALID: "Esa hora no es válida.",
        BOOKING_CLOSED: "Las reservaciones en línea están apagadas.",
        PARTY_SIZE_INVALID: "Indica cuántas personas son.",
        PARTY_SIZE_OUT_OF_RANGE: "Entre 1 y 40 personas. Para más, divide la reserva.",
        NO_AVAILABILITY: "No hay asientos suficientes a esa hora.",
        NOTES_TOO_LONG: "La nota es demasiado larga.",
        PREORDER_INVALID: "El pedido anticipado no es válido.",
      },
      emptyState: "No hay reservaciones para mostrar.",
      today: "Hoy",
      status: {
        pending: "Pendiente",
        confirmed: "Confirmada",
        seated: "Sentados",
        completed: "Finalizada",
        cancelled: "Cancelada",
      },
      actions: { confirm: "Confirmar", seat: "Sentar", complete: "Finalizar", cancel: "Cancelar" },
      attendance: {
        confirmed: "Asistencia confirmada por el cliente",
        waiting: "Esperando confirmación — si no responde, hay que llamarle",
      },
      toast: {
        newReservation: "Nueva reservación: {name}",
        newReservations: "{count} nuevas reservaciones",
        updateFailed: "No se pudo actualizar la reservación.",
      },
    },
    sr: {
      pageTitle: "White Bear Restaurant — Panel rezervacija",
      header: { reservations: "rezervacije", guests: "gostiju", refresh: "Osveži sada" },
      views: { reservations: "Rezervacije", tables: "Stolovi" },
      tables: {
        summary: "{available} od {total} mesta slobodno sada",
        square4: "Kvadratni stolovi (4)",
        rect4: "Pravougaoni stolovi (4)",
        rect6: "Pravougaoni stolovi (6)",
        rect12: "Pravougaoni sto (12)",
        rect10: "Pravougaoni sto (10)",
        table: "Sto {n}",
        seats: "{n} mesta",
        room_left: "Prednja sala — šank i ulaz",
        room_right: "Zadnja sala",
        bar: "Šank",
        entrance: "Ulaz",
        bathroom: "Toalet",
        available: "Slobodan",
        unavailable: "Nedostupan",
        hint: "Dodirnite sto na planu da ga izbacite iz upotrebe (privatni event, pokvarena stolica, itd.). Ovo smanjuje broj mesta koje sajt za klijente može da rezerviše.",
      },
      booking: {
        on: "Rezervacije uključene",
        off: "Rezervacije isključene",
        banner: "Online rezervacije su isključene. Sajt za klijente ne prima nove.",
        confirmOff:
          "Isključiti online rezervacije? Sajt za klijente će prestati da prima nove dok ih ponovo ne uključite. Već primljene rezervacije se ne menjaju, a ovde možete i dalje uneti rezervaciju primljenu telefonom.",
        confirmOn: "Ponovo uključiti online rezervacije?",
        turnedOff: "Online rezervacije su isključene.",
        turnedOn: "Online rezervacije su uključene.",
        failed: "Promena nije uspela. Proverite vezu.",
      },
      tabs: {
        today: "Danas",
        upcoming: "Predstojeće",
        all: "Sve",
        pending: "Na čekanju",
        confirmed: "Potvrđene",
        active: "Nezavršene",
        needsCall: "Treba potvrdu",
      },
      login: {
        title: "Pristup za osoblje",
        hint: "Unesite lozinku osoblja da biste videli rezervacije.",
        password: "Lozinka",
        submit: "Prijava",
        wrong: "Pogrešna lozinka.",
        failed: "Server nije dostupan. Pokušajte ponovo.",
        tooMany: "Previše neuspešnih pokušaja. Sačekajte 15 minuta i pokušajte ponovo.",
      },
      newRes: {
        open: "Nova rezervacija",
        title: "Nova rezervacija",
        name: "Ime",
        phone: "Telefon",
        date: "Datum",
        time: "Vreme",
        partySize: "Gostiju",
        seating: "Mesto",
        seatingNone: "Bez preferencije",
        seatingInside: "Unutra",
        seatingOutside: "Napolju",
        notes: "Napomene",
        cancel: "Otkaži",
        save: "Sačuvaj",
        added: "Rezervacija dodata za {name}",
        failed: "Čuvanje nije uspelo. Proverite vezu.",
      },
      errors: {
        NAME_REQUIRED: "Unesite ime (2 do 120 znakova).",
        PHONE_INVALID: "Unesite ispravan broj telefona.",
        EMAIL_INVALID: "Ta e-adresa ne izgleda ispravno.",
        DATE_INVALID: "Taj datum nije ispravan.",
        DATE_PAST: "Datum ne može biti u prošlosti.",
        DATE_TOO_FAR: "Najviše 6 meseci unapred.",
        TIME_INVALID: "To vreme nije ispravno.",
        BOOKING_CLOSED: "Online rezervacije su isključene.",
        PARTY_SIZE_INVALID: "Unesite broj gostiju.",
        PARTY_SIZE_OUT_OF_RANGE: "Između 1 i 40 gostiju. Za više, podelite rezervaciju.",
        NO_AVAILABILITY: "Nema dovoljno slobodnih mesta u to vreme.",
        NOTES_TOO_LONG: "Napomena je predugačka.",
        PREORDER_INVALID: "Narudžbina unapred nije ispravna.",
      },
      emptyState: "Nema rezervacija za prikaz.",
      today: "Danas",
      status: {
        pending: "Na čekanju",
        confirmed: "Potvrđena",
        seated: "Smešteni",
        completed: "Završena",
        cancelled: "Otkazana",
      },
      actions: { confirm: "Potvrdi", seat: "Smesti", complete: "Završi", cancel: "Otkaži" },
      attendance: {
        confirmed: "Gost je potvrdio dolazak",
        waiting: "Čeka se potvrda — pozovite ako ne odgovori",
      },
      toast: {
        newReservation: "Nova rezervacija: {name}",
        newReservations: "{count} novih rezervacija",
        updateFailed: "Rezervaciju nije bilo moguće ažurirati.",
      },
    },
  };

  function getLang() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && SUPPORTED.includes(stored)) return stored;
    } catch (err) {
      /* localStorage no disponible */
    }
    return DEFAULT_LANG;
  }

  function setLang(lang) {
    if (!SUPPORTED.includes(lang)) return;
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch (err) {
      /* ignorar */
    }
    currentLang = lang;
    document.documentElement.setAttribute("lang", lang);
    applyStaticTranslations();
    document.dispatchEvent(new CustomEvent("tablet-languagechange", { detail: { lang } }));
  }

  function resolve(dict, path) {
    return path.split(".").reduce((acc, key) => (acc && acc[key] !== undefined ? acc[key] : undefined), dict);
  }

  function interpolate(str, vars) {
    if (!vars) return str;
    return str.replace(/\{(\w+)\}/g, (match, key) => (vars[key] !== undefined ? vars[key] : match));
  }

  function t(path, vars) {
    const dict = DICTIONARIES[currentLang] || DICTIONARIES[DEFAULT_LANG];
    let value = resolve(dict, path);
    if (value === undefined) value = resolve(DICTIONARIES[DEFAULT_LANG], path);
    if (value === undefined) return path;
    return typeof value === "string" ? interpolate(value, vars) : value;
  }

  function applyStaticTranslations() {
    document.title = t("pageTitle");
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const value = t(el.getAttribute("data-i18n"));
      if (typeof value === "string") el.textContent = value;
    });
    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
      const value = t(el.getAttribute("data-i18n-title"));
      if (typeof value === "string") {
        el.setAttribute("title", value);
        // Los botones que solo llevan icono no tienen texto que leer: el
        // lector de pantalla necesita el mismo rótulo, y traducido.
        if (!el.textContent.trim()) el.setAttribute("aria-label", value);
      }
    });
    document.querySelectorAll(".lang-switcher [data-lang]").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-lang") === currentLang);
    });
  }

  function formatTime(hhmm) {
    const [h, m] = hhmm.split(":").map(Number);
    const style = TIME_STYLE[currentLang] || TIME_STYLE[DEFAULT_LANG];
    if (style === "24h") {
      return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
    }
    const period = style === "12h-es" ? (h < 12 ? "a.m." : "p.m.") : h < 12 ? "AM" : "PM";
    let h12 = h % 12;
    if (h12 === 0) h12 = 12;
    return `${h12}:${String(m).padStart(2, "0")} ${period}`;
  }

  function locale() {
    return LOCALE_MAP[currentLang] || LOCALE_MAP[DEFAULT_LANG];
  }

  let currentLang = getLang();

  global.tabletI18n = {
    SUPPORTED,
    getLang,
    setLang,
    t,
    applyStaticTranslations,
    formatTime,
    locale,
    get currentLang() {
      return currentLang;
    },
  };

  document.documentElement.setAttribute("lang", currentLang);
})(window);

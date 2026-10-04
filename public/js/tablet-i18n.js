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
      views: { reservations: "Reservations", tables: "Tables", site: "Website" },
      site: {
        banner: "The public website is CLOSED. Customers can't book online.",
        bannerAction: "Manage",
        publicTitle: "Customer website",
        online: "Open",
        offline: "Closed",
        publicHelp: "Closing it shows customers a \"we'll be right back\" page with the phone number. Online bookings and reviews stop. This panel, and guests confirming existing bookings, keep working.",
        close: "Close public website",
        reopen: "Reopen public website",
        confirmClose: "Close the public website? Customers won't be able to book online until you reopen it.",
        anyTimeTitle: "Reservations 24/7",
        anyTimeOn: "Any time, any day",
        anyTimeOff: "Opening hours only",
        anyTimeHelp: "When on, customers can book for any hour of any day. When off, only during opening hours (until 30 minutes before closing).",
        enableAnyTime: "Accept any time",
        disableAnyTime: "Opening hours only",
        passwordPrompt: "Enter the admin password to change this setting:",
        wrongPassword: "Wrong password.",
        saved: "Saved",
        failed: "Couldn't save. Check the connection.",
      },
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
      tabs: {
        today: "Today",
        upcoming: "Upcoming",
        all: "All",
        pending: "Pending",
        confirmed: "Confirmed",
        active: "Unfinished",
        needsCall: "Needs confirmation",
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
        TIME_OUT_OF_HOURS: "We're closed at that time.",
        PARTY_SIZE_INVALID: "Enter the number of guests.",
        PARTY_SIZE_OUT_OF_RANGE: "Between 1 and 40 guests. For more, split the booking.",
        TIME_PAST: "That time has already passed.",
        SITE_OFFLINE: "The public website is closed. Reopen it in the Website tab, or try again.",
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
      views: { reservations: "Reservaciones", tables: "Mesas", site: "Sitio web" },
      site: {
        banner: "El sitio web público está CERRADO. Los clientes no pueden reservar por internet.",
        bannerAction: "Gestionar",
        publicTitle: "Sitio web de clientes",
        online: "Abierto",
        offline: "Cerrado",
        publicHelp: "Al cerrarlo, los clientes ven una página de \"volvemos enseguida\" con el teléfono. Se detienen las reservas y reseñas por internet. Este panel, y la confirmación de reservas ya hechas, siguen funcionando.",
        close: "Cerrar sitio web público",
        reopen: "Reabrir sitio web público",
        confirmClose: "¿Cerrar el sitio web público? Los clientes no podrán reservar por internet hasta que lo reabras.",
        anyTimeTitle: "Reservas 24/7",
        anyTimeOn: "A cualquier hora, cualquier día",
        anyTimeOff: "Solo en horario de apertura",
        anyTimeHelp: "Activado, los clientes pueden reservar para cualquier hora de cualquier día. Desactivado, solo en horario de apertura (hasta 30 minutos antes del cierre).",
        enableAnyTime: "Aceptar a cualquier hora",
        disableAnyTime: "Solo horario de apertura",
        passwordPrompt: "Escribe la contraseña de administración para cambiar este ajuste:",
        wrongPassword: "Contraseña incorrecta.",
        saved: "Guardado",
        failed: "No se pudo guardar. Revisa la conexión.",
      },
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
      tabs: {
        today: "Hoy",
        upcoming: "Próximas",
        all: "Todas",
        pending: "Pendientes",
        confirmed: "Confirmadas",
        active: "Sin finalizar",
        needsCall: "Por confirmar",
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
        TIME_OUT_OF_HOURS: "A esa hora está cerrado.",
        PARTY_SIZE_INVALID: "Indica cuántas personas son.",
        PARTY_SIZE_OUT_OF_RANGE: "Entre 1 y 40 personas. Para más, divide la reserva.",
        TIME_PAST: "Esa hora ya pasó.",
        SITE_OFFLINE: "El sitio público está cerrado. Reábrelo en la pestaña Sitio web o inténtalo de nuevo.",
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
      views: { reservations: "Rezervacije", tables: "Stolovi", site: "Sajt" },
      site: {
        banner: "Javni sajt je ZATVOREN. Gosti ne mogu da rezervišu preko interneta.",
        bannerAction: "Upravljaj",
        publicTitle: "Sajt za goste",
        online: "Otvoren",
        offline: "Zatvoren",
        publicHelp: "Kada je zatvoren, gosti vide stranicu \"vraćamo se uskoro\" sa brojem telefona. Rezervacije i recenzije preko interneta se zaustavljaju. Ovaj panel i potvrda postojećih rezervacija i dalje rade.",
        close: "Zatvori javni sajt",
        reopen: "Ponovo otvori javni sajt",
        confirmClose: "Zatvoriti javni sajt? Gosti neće moći da rezervišu preko interneta dok ga ponovo ne otvorite.",
        anyTimeTitle: "Rezervacije 24/7",
        anyTimeOn: "Bilo kada, bilo kog dana",
        anyTimeOff: "Samo u radno vreme",
        anyTimeHelp: "Kada je uključeno, gosti mogu da rezervišu za bilo koji sat bilo kog dana. Kada je isključeno, samo u radno vreme (do 30 minuta pre zatvaranja).",
        enableAnyTime: "Prihvati bilo kada",
        disableAnyTime: "Samo radno vreme",
        passwordPrompt: "Unesite administratorsku lozinku da biste promenili ovo podešavanje:",
        wrongPassword: "Pogrešna lozinka.",
        saved: "Sačuvano",
        failed: "Čuvanje nije uspelo. Proverite vezu.",
      },
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
      tabs: {
        today: "Danas",
        upcoming: "Predstojeće",
        all: "Sve",
        pending: "Na čekanju",
        confirmed: "Potvrđene",
        active: "Nezavršene",
        needsCall: "Treba potvrdu",
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
        TIME_OUT_OF_HOURS: "U to vreme je zatvoreno.",
        PARTY_SIZE_INVALID: "Unesite broj gostiju.",
        PARTY_SIZE_OUT_OF_RANGE: "Između 1 i 40 gostiju. Za više, podelite rezervaciju.",
        TIME_PAST: "To vreme je već prošlo.",
        SITE_OFFLINE: "Javni sajt je zatvoren. Otvorite ga na kartici Sajt ili pokušajte ponovo.",
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

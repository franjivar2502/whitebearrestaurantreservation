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
      tabs: {
        today: "Today",
        upcoming: "Upcoming",
        all: "All",
        pending: "Pending",
        confirmed: "Confirmed",
        active: "Unfinished",
        needsCall: "⏳ Needs confirmation",
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
        confirmed: "✅ Attendance confirmed by the guest",
        waiting: "⏳ Waiting for confirmation — call if they don't respond",
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
      tabs: {
        today: "Hoy",
        upcoming: "Próximas",
        all: "Todas",
        pending: "Pendientes",
        confirmed: "Confirmadas",
        active: "Sin finalizar",
        needsCall: "⏳ Por confirmar",
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
        confirmed: "✅ Asistencia confirmada por el cliente",
        waiting: "⏳ Esperando confirmación — si no responde, hay que llamarle",
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
      tabs: {
        today: "Danas",
        upcoming: "Predstojeće",
        all: "Sve",
        pending: "Na čekanju",
        confirmed: "Potvrđene",
        active: "Nezavršene",
        needsCall: "⏳ Treba potvrdu",
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
        confirmed: "✅ Gost je potvrdio dolazak",
        waiting: "⏳ Čeka se potvrda — pozovite ako ne odgovori",
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
      if (typeof value === "string") el.setAttribute("title", value);
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

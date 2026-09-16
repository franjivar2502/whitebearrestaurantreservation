/*
 * Sistema de traducción (inglés por defecto, español y francés).
 * Diccionario centralizado + helpers para aplicar textos estáticos vía
 * data-i18n, traducir strings dinámicos, y formatear fecha/hora según
 * el idioma activo. Todas las páginas del sitio cargan este archivo
 * antes de su propio script.
 */
(function (global) {
  const STORAGE_KEY = "wb-lang";
  const DEFAULT_LANG = "en";
  const SUPPORTED = ["en", "es", "fr"];

  const LOCALE_MAP = { en: "en-US", es: "es-ES", fr: "fr-FR" };
  const TIME_STYLE = { en: "12h-en", es: "12h-es", fr: "24h" };

  const DAY_NAMES = {
    en: { mon: "Monday", tue: "Tuesday", wed: "Wednesday", thu: "Thursday", fri: "Friday", sat: "Saturday", sun: "Sunday" },
    es: { mon: "Lunes", tue: "Martes", wed: "Miércoles", thu: "Jueves", fri: "Viernes", sat: "Sábado", sun: "Domingo" },
    fr: { mon: "Lundi", tue: "Mardi", wed: "Mercredi", thu: "Jeudi", fri: "Vendredi", sat: "Samedi", sun: "Dimanche" },
  };

  const JOIN_WORDS = {
    en: { pair: "and", range: "to" },
    es: { pair: "y", range: "a" },
    fr: { pair: "et", range: "à" },
  };

  const DICTIONARIES = {
    en: {
      hero: {
        reviews: "reviews",
        perPerson: "per person",
        category: "Restaurant",
      },
      gallery: {
        title: "Gallery",
      },
      map: {
        title: "Find us",
      },
      about: {
        title: "About us",
        description:
          "Dine-in · Takeout · Delivery. Guests highlight generous portions, a great variety on the menu, friendly staff and a wonderful atmosphere.",
      },
      info: {
        title: "Venue information",
        seeAll: "See all ▾",
        seeLess: "See less ▴",
        groups: {
          accessibility: { title: "♿ Accessibility", items: ["Wheelchair accessible seating", "Wheelchair accessible parking lot", "Wheelchair accessible restroom"] },
          service: { title: "🍽️ Service options", items: ["Outdoor seating", "Takeout", "Dine-in", "Delivery"] },
          highlights: { title: "⭐ Highlights", items: ["Fast service", "Great cocktails", "Great desserts", "Offers regional specialties"] },
          popular: { title: "🔥 Popular for", items: ["Lunch", "Dinner", "Solo dining"] },
          offers: { title: "🍷 Offerings", items: ["Alcohol", "Appetizers", "Hard liquor", "Coffee", "Beer", "Cocktails", "Comfort food", "Wine"] },
          diningOptions: { title: "🏠 Dining options", items: ["Lunch", "Dinner", "Dessert", "Seating", "Table service"] },
          amenities: { title: "🧰 Amenities", items: ["Restroom", "Has a bar"] },
          atmosphere: { title: "✨ Atmosphere", items: ["Cozy", "Casual"] },
          crowd: { title: "👥 Crowd", items: ["Groups", "Tourists"] },
          planning: { title: "📅 Planning", items: ["Accepts reservations"] },
          payments: { title: "💳 Payments", items: ["Credit cards", "Debit cards"] },
          children: { title: "👶 Children", items: ["Good for kids", "Kids' menu", "High chairs"] },
          parking: { title: "🅿️ Parking", items: ["Plenty of parking", "On-site parking", "Free parking", "Free street parking", "Paid parking"] },
          pets: { title: "🐾 Pets", items: ["Dogs allowed outside"] },
        },
      },
      form: {
        title: "Reserve your table",
        subtitle: "We confirm by phone or email, and let you know when your table is ready.",
        name: "Full name *",
        phone: "Phone *",
        phoneHint: "We'll send your confirmation and a table-ready alert here.",
        email: "Email (optional)",
        emailHint:
          "Leave your email to also get the confirmation and table-ready alert there. It also lets us ask for your feedback after your visit.",
        date: "Date *",
        time: "Time *",
        timeHint: "{day}: reservations from {open} to {close}",
        partySize: "Party size *",
        partySizeHint: "Groups larger than {max}: call {phone}.",
        occasion: "Occasion (optional)",
        occasionNone: "None",
        occasionBirthday: "Birthday",
        occasionAnniversary: "Anniversary",
        occasionBusiness: "Business meeting",
        occasionOther: "Other",
        notes: "Notes or special requests",
        notesPlaceholder: "Allergies, high chair, outdoor table, etc.",
        submit: "Book table",
        submitting: "Sending...",
      },
      groupMenu: {
        title: "Large group pre-order",
        badge: "{threshold}+ people",
        note: "For groups of {threshold} people or more, we offer a limited menu. Pre-order here and we'll have your order ready to review when you arrive.",
        notesLabel: "Order notes (allergies, restrictions, etc.)",
        notesPlaceholder: "E.g. 3 people are vegetarian",
        hint: "You can leave this blank and order when you arrive; filling it in ahead just helps us have everything ready sooner.",
        emptyMenu: "The group menu isn't set yet; staff will help you decide when you arrive.",
      },
      confirmation: {
        title: "Reservation received!",
        subtitle:
          "We look forward to seeing you at White Bear Restaurant. We've sent your confirmation by phone/email, and we'll let you know 15 minutes before your time when your table is ready.",
        name: "Name",
        date: "Date",
        time: "Time",
        partySize: "Party size",
        phone: "Phone",
        email: "Email",
        code: "Code",
        preorder: "Pre-order",
        newReservation: "Make another reservation",
      },
      footer: {
        staffQuestion: "Are you staff?",
        staffLinkText: "Open the reservations panel",
      },
      errors: {
        NAME_REQUIRED: "Name is required.",
        PHONE_INVALID: "Enter a valid phone number.",
        EMAIL_INVALID: "That email address isn't valid.",
        DATE_INVALID: "Select a valid date.",
        DATE_PAST: "The date can't be in the past.",
        TIME_INVALID: "Select a valid time.",
        TIME_OUT_OF_HOURS: "We take reservations that day between {open} and {close}.",
        PARTY_SIZE_INVALID: "Enter a valid party size.",
        PARTY_SIZE_OUT_OF_RANGE: "Party size must be between 1 and {max}. For larger groups, call {phone}.",
        PREORDER_INVALID: "The group pre-order isn't valid.",
        GENERIC: "Something went wrong. Please try again.",
        NETWORK: "Couldn't reach the server. Please try again.",
      },
      confirmPage: {
        pageTitle: "Confirm your attendance — White Bear Restaurant",
        loading: "Loading your reservation…",
        notFoundTitle: "We couldn't find that reservation",
        notFoundText: "Check the link we sent you, or call the restaurant at {phone} to confirm directly.",
        question: "Will you be joining us?",
        expecting: "White Bear Restaurant is expecting you:",
        yes: "✅ Yes, I'll be there",
        no: "I can't make it",
        callHint: "If you have questions, call the restaurant at {phone}.",
        alreadyCancelledTitle: "This reservation is already cancelled",
        alreadyCancelledText: "If this was a mistake, call the restaurant at {phone}.",
        alreadyConfirmedTitle: "You already confirmed your attendance!",
        seeYou: "We'll see you on {date} at {time}.",
        confirmedTitle: "Attendance confirmed!",
        confirmedText: "We'll see you on {date} at {time} — thanks for confirming.",
        declinedTitle: "Reservation cancelled",
        declinedText: "Thanks for letting us know. We hope to see you another time.",
        sendErrorTitle: "We couldn't send your response",
        sendErrorText: "Try again, or call the restaurant at {phone}.",
      },
      common: {
        name: "Name",
        date: "Date",
        time: "Time",
        partySize: "Party size",
      },
    },

    es: {
      hero: {
        reviews: "reseñas",
        perPerson: "por persona",
        category: "Restaurante",
      },
      gallery: {
        title: "Galería",
      },
      map: {
        title: "Cómo llegar",
      },
      about: {
        title: "Sobre nosotros",
        description:
          "Consumo en el lugar · Para llevar · Entrega a domicilio. Comensales destacan porciones generosas, gran variedad en el menú, personal amable y un ambiente excelente.",
      },
      info: {
        title: "Información del lugar",
        seeAll: "Ver todo ▾",
        seeLess: "Ver menos ▴",
        groups: {
          accessibility: { title: "♿ Accesibilidad", items: ["Espacio accesible para personas en silla de ruedas", "Estacionamiento accesible para personas en silla de ruedas", "Sanitarios accesibles para personas en silla de ruedas"] },
          service: { title: "🍽️ Opciones de servicio", items: ["Asientos al aire libre", "Para llevar", "Consumo en el lugar", "Entrega a domicilio"] },
          highlights: { title: "⭐ Aspectos destacados", items: ["Atención rápida", "Buenos cócteles", "Deliciosos postres", "Ofrece especialidades de la región"] },
          popular: { title: "🔥 Popular por", items: ["Almuerzo", "Cena", "Cena en solitario"] },
          offers: { title: "🍷 Qué ofrece", items: ["Alcohol", "Aperitivos", "Bebidas fuertes", "Café", "Cerveza", "Cócteles", "Comida casera", "Vino"] },
          diningOptions: { title: "🏠 Opciones del local", items: ["Almuerzo", "Cena", "Postres", "Espacio con asientos", "Servicio a la mesa"] },
          amenities: { title: "🧰 Servicios", items: ["Sanitario", "Tiene bar"] },
          atmosphere: { title: "✨ Ambiente", items: ["Agradable", "Informal"] },
          crowd: { title: "👥 Público usual", items: ["Grupos", "Turistas"] },
          planning: { title: "📅 Planificación", items: ["Se aceptan reservas"] },
          payments: { title: "💳 Pagos", items: ["Tarjetas de crédito", "Tarjetas de débito"] },
          children: { title: "👶 Menores", items: ["Ideal para ir con niños", "Menú para niños", "Sillas altas"] },
          parking: { title: "🅿️ Estacionamiento", items: ["Hay suficiente espacio", "Estacionamiento en el lugar", "Estacionamiento gratuito", "Estacionamiento gratuito en la calle", "Estacionamiento pagado"] },
          pets: { title: "🐾 Mascotas", items: ["Se permiten perros afuera"] },
        },
      },
      form: {
        title: "Reserva tu mesa",
        subtitle: "Te confirmamos por teléfono o correo, y avisamos cuando tu mesa esté lista.",
        name: "Nombre completo *",
        phone: "Teléfono *",
        phoneHint: "Te enviaremos por aquí la confirmación y un aviso cuando tu mesa esté lista.",
        email: "Correo electrónico (opcional)",
        emailHint:
          "Déjanos tu correo para recibir también ahí la confirmación y el aviso de mesa lista. Además, nos permite pedirte tu opinión sobre tu visita después de la reservación.",
        date: "Fecha *",
        time: "Hora *",
        timeHint: "{day}: reservaciones de {open} a {close}",
        partySize: "Número de personas *",
        partySizeHint: "Grupos de más de {max}: llama al {phone}.",
        occasion: "Ocasión (opcional)",
        occasionNone: "Ninguna",
        occasionBirthday: "Cumpleaños",
        occasionAnniversary: "Aniversario",
        occasionBusiness: "Cita de negocios",
        occasionOther: "Otro",
        notes: "Notas o solicitudes especiales",
        notesPlaceholder: "Alergias, silla para bebé, mesa afuera, etc.",
        submit: "Reservar mesa",
        submitting: "Enviando...",
      },
      groupMenu: {
        title: "Preorden para grupos grandes",
        badge: "{threshold}+ personas",
        note: "Para grupos de {threshold} personas o más ofrecemos un menú reducido. Preordena aquí y tendremos tu pedido listo para revisar cuando llegues.",
        notesLabel: "Notas del pedido (alergias, restricciones, etc.)",
        notesPlaceholder: "Ej. 3 personas son vegetarianas",
        hint: "Puedes dejarlo en blanco y ordenar al llegar; llenarlo por adelantado solo nos ayuda a tener todo listo antes.",
        emptyMenu: "El menú de grupo aún no está disponible; el staff te ayudará a definir el pedido al llegar.",
      },
      confirmation: {
        title: "¡Reservación recibida!",
        subtitle:
          "Te esperamos en White Bear Restaurant. Te enviamos la confirmación por teléfono/correo, y te avisaremos 15 minutos antes de tu hora cuando la mesa esté lista.",
        name: "Nombre",
        date: "Fecha",
        time: "Hora",
        partySize: "Personas",
        phone: "Teléfono",
        email: "Correo",
        code: "Código",
        preorder: "Preorden",
        newReservation: "Hacer otra reservación",
      },
      footer: {
        staffQuestion: "¿Eres del staff?",
        staffLinkText: "Abrir panel de reservaciones",
      },
      errors: {
        NAME_REQUIRED: "El nombre es obligatorio.",
        PHONE_INVALID: "Ingresa un teléfono válido.",
        EMAIL_INVALID: "El correo electrónico no es válido.",
        DATE_INVALID: "Selecciona una fecha válida.",
        DATE_PAST: "La fecha no puede ser en el pasado.",
        TIME_INVALID: "Selecciona una hora válida.",
        TIME_OUT_OF_HOURS: "Ese día recibimos reservaciones entre las {open} y las {close}.",
        PARTY_SIZE_INVALID: "Ingresa un número de personas válido.",
        PARTY_SIZE_OUT_OF_RANGE: "El número de personas debe ser entre 1 y {max}. Para grupos más grandes, llama al {phone}.",
        PREORDER_INVALID: "El preorden del grupo no es válido.",
        GENERIC: "Ocurrió un error. Intenta de nuevo.",
        NETWORK: "No se pudo conectar con el servidor. Intenta de nuevo.",
      },
      confirmPage: {
        pageTitle: "Confirma tu asistencia — White Bear Restaurant",
        loading: "Cargando tu reservación…",
        notFoundTitle: "No encontramos esa reservación",
        notFoundText: "Revisa el link que te enviamos, o llama al restaurante al {phone} para confirmar directamente.",
        question: "¿Confirmas tu asistencia?",
        expecting: "White Bear Restaurant te espera:",
        yes: "✅ Sí, confirmo mi asistencia",
        no: "No podré asistir",
        callHint: "Si tienes dudas, llama al restaurante al {phone}.",
        alreadyCancelledTitle: "Esta reservación ya está cancelada",
        alreadyCancelledText: "Si fue un error, llama al restaurante al {phone}.",
        alreadyConfirmedTitle: "¡Ya habías confirmado tu asistencia!",
        seeYou: "Te esperamos el {date} a las {time}.",
        confirmedTitle: "¡Asistencia confirmada!",
        confirmedText: "Te esperamos el {date} a las {time}, gracias por confirmar.",
        declinedTitle: "Reservación cancelada",
        declinedText: "Gracias por avisarnos. Esperamos verte en otra ocasión.",
        sendErrorTitle: "No se pudo enviar tu respuesta",
        sendErrorText: "Intenta de nuevo, o llama al restaurante al {phone}.",
      },
      common: {
        name: "Nombre",
        date: "Fecha",
        time: "Hora",
        partySize: "Personas",
      },
    },

    fr: {
      hero: {
        reviews: "avis",
        perPerson: "par personne",
        category: "Restaurant",
      },
      gallery: {
        title: "Galerie",
      },
      map: {
        title: "Nous trouver",
      },
      about: {
        title: "À propos",
        description:
          "Sur place · À emporter · Livraison. Les clients soulignent des portions généreuses, une grande variété au menu, un personnel aimable et une ambiance excellente.",
      },
      info: {
        title: "Informations sur l'établissement",
        seeAll: "Voir tout ▾",
        seeLess: "Voir moins ▴",
        groups: {
          accessibility: { title: "♿ Accessibilité", items: ["Places accessibles en fauteuil roulant", "Stationnement accessible en fauteuil roulant", "Toilettes accessibles en fauteuil roulant"] },
          service: { title: "🍽️ Options de service", items: ["Places assises en extérieur", "À emporter", "Sur place", "Livraison"] },
          highlights: { title: "⭐ Points forts", items: ["Service rapide", "Bons cocktails", "Excellents desserts", "Propose des spécialités régionales"] },
          popular: { title: "🔥 Réputé pour", items: ["Déjeuner", "Dîner", "Dîner en solo"] },
          offers: { title: "🍷 Propose", items: ["Alcool", "Apéritifs", "Alcools forts", "Café", "Bière", "Cocktails", "Cuisine maison", "Vin"] },
          diningOptions: { title: "🏠 Options sur place", items: ["Déjeuner", "Dîner", "Desserts", "Places assises", "Service à table"] },
          amenities: { title: "🧰 Services", items: ["Toilettes", "Bar sur place"] },
          atmosphere: { title: "✨ Ambiance", items: ["Chaleureuse", "Décontractée"] },
          crowd: { title: "👥 Clientèle", items: ["Groupes", "Touristes"] },
          planning: { title: "📅 Organisation", items: ["Réservations acceptées"] },
          payments: { title: "💳 Paiements", items: ["Cartes de crédit", "Cartes de débit"] },
          children: { title: "👶 Enfants", items: ["Convient aux enfants", "Menu enfant", "Chaises hautes"] },
          parking: { title: "🅿️ Stationnement", items: ["Places suffisantes", "Parking sur place", "Stationnement gratuit", "Stationnement gratuit dans la rue", "Stationnement payant"] },
          pets: { title: "🐾 Animaux", items: ["Chiens autorisés en terrasse"] },
        },
      },
      form: {
        title: "Réservez votre table",
        subtitle: "Nous confirmons par téléphone ou e-mail, et vous prévenons quand votre table est prête.",
        name: "Nom complet *",
        phone: "Téléphone *",
        phoneHint: "Nous vous enverrons ici la confirmation et une alerte quand votre table sera prête.",
        email: "E-mail (facultatif)",
        emailHint:
          "Laissez-nous votre e-mail pour recevoir aussi la confirmation et l'alerte de table prête. Cela nous permet aussi de vous demander votre avis après votre visite.",
        date: "Date *",
        time: "Heure *",
        timeHint: "{day} : réservations de {open} à {close}",
        partySize: "Nombre de personnes *",
        partySizeHint: "Groupes de plus de {max} personnes : appelez le {phone}.",
        occasion: "Occasion (facultatif)",
        occasionNone: "Aucune",
        occasionBirthday: "Anniversaire",
        occasionAnniversary: "Anniversaire de mariage",
        occasionBusiness: "Rendez-vous d'affaires",
        occasionOther: "Autre",
        notes: "Notes ou demandes spéciales",
        notesPlaceholder: "Allergies, chaise haute, table extérieure, etc.",
        submit: "Réserver une table",
        submitting: "Envoi en cours...",
      },
      groupMenu: {
        title: "Précommande pour grands groupes",
        badge: "{threshold}+ personnes",
        note: "Pour les groupes de {threshold} personnes ou plus, nous proposons un menu réduit. Précommandez ici et votre commande sera prête à valider à votre arrivée.",
        notesLabel: "Notes de commande (allergies, restrictions, etc.)",
        notesPlaceholder: "Ex. 3 personnes sont végétariennes",
        hint: "Vous pouvez laisser ce champ vide et commander à votre arrivée ; le remplir à l'avance nous aide simplement à tout préparer plus tôt.",
        emptyMenu: "Le menu de groupe n'est pas encore défini ; le personnel vous aidera à votre arrivée.",
      },
      confirmation: {
        title: "Réservation reçue !",
        subtitle:
          "Nous avons hâte de vous accueillir au White Bear Restaurant. Nous vous avons envoyé la confirmation par téléphone/e-mail, et nous vous préviendrons 15 minutes avant l'heure quand votre table sera prête.",
        name: "Nom",
        date: "Date",
        time: "Heure",
        partySize: "Personnes",
        phone: "Téléphone",
        email: "E-mail",
        code: "Code",
        preorder: "Précommande",
        newReservation: "Faire une autre réservation",
      },
      footer: {
        staffQuestion: "Vous faites partie du personnel ?",
        staffLinkText: "Ouvrir le panneau des réservations",
      },
      errors: {
        NAME_REQUIRED: "Le nom est obligatoire.",
        PHONE_INVALID: "Entrez un numéro de téléphone valide.",
        EMAIL_INVALID: "L'adresse e-mail n'est pas valide.",
        DATE_INVALID: "Sélectionnez une date valide.",
        DATE_PAST: "La date ne peut pas être dans le passé.",
        TIME_INVALID: "Sélectionnez une heure valide.",
        TIME_OUT_OF_HOURS: "Ce jour-là, nous prenons les réservations entre {open} et {close}.",
        PARTY_SIZE_INVALID: "Entrez un nombre de personnes valide.",
        PARTY_SIZE_OUT_OF_RANGE: "Le nombre de personnes doit être entre 1 et {max}. Pour les groupes plus grands, appelez le {phone}.",
        PREORDER_INVALID: "La précommande du groupe n'est pas valide.",
        GENERIC: "Une erreur s'est produite. Veuillez réessayer.",
        NETWORK: "Impossible de contacter le serveur. Veuillez réessayer.",
      },
      confirmPage: {
        pageTitle: "Confirmez votre présence — White Bear Restaurant",
        loading: "Chargement de votre réservation…",
        notFoundTitle: "Réservation introuvable",
        notFoundText: "Vérifiez le lien que nous vous avons envoyé, ou appelez le restaurant au {phone} pour confirmer directement.",
        question: "Confirmez-vous votre présence ?",
        expecting: "White Bear Restaurant vous attend :",
        yes: "✅ Oui, je confirme ma présence",
        no: "Je ne pourrai pas venir",
        callHint: "Pour toute question, appelez le restaurant au {phone}.",
        alreadyCancelledTitle: "Cette réservation est déjà annulée",
        alreadyCancelledText: "S'il s'agit d'une erreur, appelez le restaurant au {phone}.",
        alreadyConfirmedTitle: "Vous aviez déjà confirmé votre présence !",
        seeYou: "Nous vous attendons le {date} à {time}.",
        confirmedTitle: "Présence confirmée !",
        confirmedText: "Nous vous attendons le {date} à {time}, merci d'avoir confirmé.",
        declinedTitle: "Réservation annulée",
        declinedText: "Merci de nous avoir prévenus. Nous espérons vous voir une prochaine fois.",
        sendErrorTitle: "Impossible d'envoyer votre réponse",
        sendErrorText: "Réessayez, ou appelez le restaurant au {phone}.",
      },
      common: {
        name: "Nom",
        date: "Date",
        time: "Heure",
        partySize: "Personnes",
      },
    },
  };

  function getLang() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && SUPPORTED.includes(stored)) return stored;
    } catch (err) {
      /* localStorage no disponible: usamos el idioma por defecto */
    }
    return DEFAULT_LANG;
  }

  function setLang(lang) {
    if (!SUPPORTED.includes(lang)) return;
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch (err) {
      /* ignorar si localStorage no está disponible */
    }
    currentLang = lang;
    document.documentElement.setAttribute("lang", lang);
    applyStaticTranslations();
    document.dispatchEvent(new CustomEvent("languagechange", { detail: { lang } }));
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
    if (value === undefined) {
      value = resolve(DICTIONARIES[DEFAULT_LANG], path);
    }
    if (value === undefined) return path;
    return typeof value === "string" ? interpolate(value, vars) : value;
  }

  function applyStaticTranslations() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const value = t(el.getAttribute("data-i18n"));
      if (typeof value === "string") el.textContent = value;
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const value = t(el.getAttribute("data-i18n-placeholder"));
      if (typeof value === "string") el.setAttribute("placeholder", value);
    });
    document.querySelectorAll("[data-i18n-html]").forEach((el) => {
      const value = t(el.getAttribute("data-i18n-html"));
      if (typeof value === "string") el.innerHTML = value;
    });
    document.querySelectorAll(".lang-switcher [data-lang]").forEach((btn) => {
      const isActive = btn.getAttribute("data-lang") === currentLang;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-pressed", String(isActive));
    });
  }

  function formatDateLong(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    const date = new Date(y, m - 1, d);
    return date.toLocaleDateString(LOCALE_MAP[currentLang] || LOCALE_MAP[DEFAULT_LANG], {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
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

  function dayKeyForDate(iso) {
    const order = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
    const [y, m, d] = iso.split("-").map(Number);
    const date = new Date(y, m - 1, d);
    return order[(date.getDay() + 6) % 7];
  }

  function dayName(key) {
    return (DAY_NAMES[currentLang] || DAY_NAMES[DEFAULT_LANG])[key];
  }

  function joinWord(kind) {
    return (JOIN_WORDS[currentLang] || JOIN_WORDS[DEFAULT_LANG])[kind];
  }

  function getInfoGroups() {
    const dict = DICTIONARIES[currentLang] || DICTIONARIES[DEFAULT_LANG];
    return (dict.info && dict.info.groups) || DICTIONARIES[DEFAULT_LANG].info.groups;
  }

  let currentLang = getLang();

  global.i18n = {
    SUPPORTED,
    getLang,
    setLang,
    t,
    applyStaticTranslations,
    formatDateLong,
    formatTime,
    dayKeyForDate,
    dayName,
    joinWord,
    getInfoGroups,
    get currentLang() {
      return currentLang;
    },
  };

  document.documentElement.setAttribute("lang", currentLang);
})(window);

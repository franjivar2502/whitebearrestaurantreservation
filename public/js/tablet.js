(function () {
  const listEl = document.getElementById("reservation-list");
  const emptyState = document.getElementById("empty-state");
  const statTotal = document.getElementById("stat-total");
  const statGuests = document.getElementById("stat-guests");
  const clockEl = document.getElementById("clock");
  const toastEl = document.getElementById("toast");
  const refreshBtn = document.getElementById("refresh-btn");
  const langSwitcher = document.getElementById("lang-switcher");
  const viewTabs = document.querySelectorAll(".view-tab");
  const reservationsView = document.getElementById("reservations-view");
  const tablesView = document.getElementById("tables-view");
  const tablesSummary = document.getElementById("tables-summary");
  const floorPlan = document.getElementById("floor-plan");
  const bookingToggle = document.getElementById("booking-toggle");
  const bookingToggleLabel = document.getElementById("booking-toggle-label");
  const bookingBanner = document.getElementById("booking-banner");

  const dateTabs = document.querySelectorAll(".tab[data-filter]");
  const statusTabs = document.querySelectorAll(".tab[data-status]");

  /* Iconos de línea en vez de emojis. Los emojis se dibujan distinto en cada
     sistema (y en color), así que en una herramienta de trabajo quedan
     desiguales; estos heredan el color del texto y pesan unos bytes. */
  const ICON_PATHS = {
    people: "M16 19v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 17.5V19M10 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7M20 19v-1.5a3.5 3.5 0 0 0-2.6-3.4M15.4 4.6a3.5 3.5 0 0 1 0 6.8",
    phone: "M15.5 20A11.5 11.5 0 0 1 4 8.5V6.6A1.6 1.6 0 0 1 5.6 5h2.1c.5 0 .9.3 1 .8l.8 3c.1.4 0 .8-.4 1l-1.4 1a9.6 9.6 0 0 0 4.5 4.5l1-1.4c.2-.4.6-.5 1-.4l3 .8c.5.1.8.5.8 1v2.1A1.6 1.6 0 0 1 17.4 20z",
    mail: "M4 7h16v11H4zM4 7l8 6 8-6",
    hash: "M6 9h13M5 15h13M11 4 9 20M16 4l-2 16",
    note: "M6 4h8l4 4v12H6zM14 4v4h4M9 13h6M9 16.5h4",
    clock: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18M12 7.5V12l3 2",
  };

  function icon(name) {
    return `<svg class="i" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="${ICON_PATHS[name]}"/></svg>`;
  }

  let dateFilter = "today"; // today | upcoming | all
  let statusFilter = "active"; // active | pending | confirmed
  let reservations = [];
  let pollTimer = null;
  let lastSeenIds = new Set();
  let firstLoad = true;
  let currentView = "reservations"; // reservations | tables
  let tables = [];
  let rooms = [];
  let totalSeats = 0;
  let availableSeats = 0;
  let bookingEnabled = true;

  tabletI18n.applyStaticTranslations();

  langSwitcher.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-lang]");
    if (!btn) return;
    tabletI18n.setLang(btn.getAttribute("data-lang"));
  });

  document.addEventListener("tablet-languagechange", () => {
    updateClock();
    renderBookingToggle();
    render();
    if (currentView === "tables" && tables.length) renderTables(totalSeats, availableSeats);
  });

  function todayIso() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  /* Fecha y hora van en elementos separados para que en pantallas estrechas
     el CSS pueda esconder la fecha y dejar la hora, que es lo que se mira. */
  function updateClock() {
    const now = new Date();
    const date = now.toLocaleDateString(tabletI18n.locale(), {
      weekday: "long",
      day: "numeric",
      month: "long",
    });
    const time = now.toLocaleTimeString(tabletI18n.locale(), {
      hour: "2-digit",
      minute: "2-digit",
    });
    clockEl.innerHTML =
      `<span class="clock-date">${escapeHtml(date)} · </span>` +
      `<span class="clock-time">${escapeHtml(time)}</span>`;
  }

  function formatDayHeading(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    const date = new Date(y, m - 1, d);
    const isToday = iso === todayIso();
    const label = date.toLocaleDateString(tabletI18n.locale(), {
      weekday: "long",
      day: "numeric",
      month: "long",
    });
    return isToday ? `${tabletI18n.t("today")} · ${label}` : label;
  }

  function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str == null ? "" : str;
    return d.innerHTML;
  }

  /* Para texto dentro de un atributo hace falta otra cosa que escapeHtml.
     Aquel pasa por textContent/innerHTML, que escapa < y & pero deja pasar
     las comillas -- y la comilla es el carácter con el que uno se sale de
     src="..." para colar un onerror. */
  function escapeAttr(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function showToast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    setTimeout(() => toastEl.classList.remove("show"), 2500);
  }

  async function fetchReservations() {
    try {
      const res = await fetch("/api/reservations", { cache: "no-store" });
      if (!res.ok) throw new Error("bad status");
      const data = await res.json();

      if (!firstLoad) {
        const newOnes = data.filter((r) => !lastSeenIds.has(r.id));
        if (newOnes.length > 0) {
          showToast(
            newOnes.length === 1
              ? tabletI18n.t("toast.newReservation", { name: newOnes[0].name })
              : tabletI18n.t("toast.newReservations", { count: newOnes.length })
          );
        }
      }
      lastSeenIds = new Set(data.map((r) => r.id));
      firstLoad = false;

      reservations = data;
      render();
    } catch (err) {
      // Falla silenciosa: se reintenta en el próximo ciclo de polling.
    }
  }

  /*
   * Plano del salón. Las mesas llegan del servidor con su salón y su posición
   * (x,y en % del salón, ver TABLE_LAYOUT en server.py); aquí solo se dibujan.
   * El tamaño sale de la forma y los asientos, para que la de 12 se vea como
   * una de 12 y el staff la reconozca sin leer el número.
   *
   * Lo que no es mesa -- barra, entrada, baño, ventanas -- es decorado para
   * orientarse y vive solo aquí: no tiene estado ni lo toca nadie por la API.
   * Su x/y/w/h va en % desde la esquina superior izquierda del salón; los
   * valores fuera de 0-100 son a propósito, para montarse sobre la pared.
   */
  /* Banquetas de la barra. Se generan en vez de escribir once objetos casi
     iguales: así cambiar el número o el tramo que ocupan es tocar un dato.
     El bar va pegado a la pared izquierda (x 3-19%), de modo que las sillas
     solo caben por su lado abierto, el derecho.

     Son decorativas: ayudan al personal a reconocer el salón, pero NO suman
     asientos reservables. La barra se ocupa sin reserva. */
  const BAR_STOOLS = 11;
  const barStools = Array.from({ length: BAR_STOOLS }, (_, i) => ({
    kind: "stool",
    x: 20.5,
    y: 29 + (i * 58) / (BAR_STOOLS - 1),
  }));

  const ROOM_FIXTURES = {
    left: [
      { kind: "bar", x: 3, y: 26, w: 16, h: 66, labelKey: "tables.bar" },
      ...barStools,
      { kind: "door", x: 36, y: -3, w: 17, h: 6, labelKey: "tables.entrance" },
      { kind: "door", x: 41, y: 97, w: 19, h: 6, labelKey: "tables.bathroom" },
      { kind: "window", x: -1.5, y: 5, w: 3, h: 18 },
      { kind: "window", x: 13, y: -1.5, w: 16, h: 3 },
      { kind: "window", x: 60, y: -1.5, w: 22, h: 3 },
    ],
    right: [
      { kind: "window", x: 8, y: -1.5, w: 26, h: 3 },
      { kind: "window", x: 44, y: -1.5, w: 32, h: 3 },
      { kind: "window", x: 98.5, y: 14, w: 3, h: 15 },
      { kind: "window", x: 98.5, y: 41, w: 3, h: 15 },
      { kind: "window", x: 98.5, y: 64, w: 3, h: 13 },
      { kind: "window", x: 98.5, y: 85, w: 3, h: 11 },
    ],
  };

  function tableSize(t) {
    if (t.seats >= 12) return { w: 36, h: 9 };
    if (t.seats >= 10) return { w: 30, h: 9 };
    if (t.shape === "square") return { w: 12, h: 9 };
    return t.seats >= 6 ? { w: 20, h: 8 } : { w: 16, h: 8 };
  }

  async function fetchTables() {
    try {
      const res = await fetch("/api/tables", { cache: "no-store" });
      if (!res.ok) throw new Error("bad status");
      const data = await res.json();
      tables = data.tables || [];
      rooms = data.rooms || [];
      totalSeats = data.totalSeats;
      availableSeats = data.availableSeats;
      renderTables(totalSeats, availableSeats);
    } catch (err) {
      // Falla silenciosa: se reintenta en el próximo ciclo de polling.
    }
  }

  function renderTables(totalSeats, availableSeats) {
    tablesSummary.textContent = tabletI18n.t("tables.summary", {
      available: availableSeats,
      total: totalSeats,
    });

    floorPlan.innerHTML = rooms
      .map((room) => {
        const fixtures = (ROOM_FIXTURES[room] || [])
          .map((f) => {
            const label = f.labelKey
              ? `<span class="floor-fixture-label">${escapeHtml(tabletI18n.t(f.labelKey))}</span>`
              : "";
            /* Las banquetas no llevan ancho ni alto en %: un círculo definido
               en porcentajes se deforma en óvalo al cambiar el tamaño del
               salón, porque el % de ancho y el de alto miden cosas distintas.
               Van con tamaño fijo en el CSS y aquí solo su posición. */
            const box =
              f.kind === "stool"
                ? ""
                : `width:${f.w}%;height:${f.h}%;`;
            return `<div class="floor-fixture floor-fixture--${f.kind}" style="left:${f.x}%;top:${f.y}%;${box}">${label}</div>`;
          })
          .join("");

        const tiles = tables
          .filter((t) => t.room === room)
          .map((t) => {
            const size = tableSize(t);
            const label = tabletI18n.t("tables.table", { n: t.number });
            const state = tabletI18n.t(t.unavailable ? "tables.unavailable" : "tables.available");
            return `
              <button type="button"
                class="floor-table ${t.unavailable ? "unavailable" : "available"} ${t.shape === "square" ? "is-square" : "is-rect"}"
                style="left:${t.x}%;top:${t.y}%;width:${size.w}%;height:${size.h}%"
                data-id="${escapeAttr(t.id)}"
                aria-label="${escapeAttr(`${label} — ${tabletI18n.t("tables.seats", { n: t.seats })} — ${state}`)}">
                <span class="floor-table-num">${escapeHtml(String(t.number))}</span>
                <span class="floor-table-seats">${escapeHtml(tabletI18n.t("tables.seats", { n: t.seats }))}</span>
              </button>`;
          })
          .join("");

        return `
          <div class="floor-room floor-room--${room}">
            <p class="floor-room-title">${escapeHtml(tabletI18n.t(`tables.room_${room}`))}</p>
            <div class="floor-room-box">${fixtures}${tiles}</div>
          </div>`;
      })
      .join("");

    floorPlan.querySelectorAll(".floor-table").forEach((btn) => {
      btn.addEventListener("click", () => toggleTable(btn.getAttribute("data-id")));
    });
  }

  async function toggleTable(id) {
    const t = tables.find((x) => x.id === id);
    if (!t) return;
    const nextUnavailable = !t.unavailable;
    try {
      const res = await fetch(`/api/tables/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ unavailable: nextUnavailable }),
      });
      if (!res.ok) throw new Error("update failed");
      fetchTables();
    } catch (err) {
      showToast(tabletI18n.t("toast.updateFailed"));
    }
  }

  /* ---------- interruptor de reservaciones ----------
     Apaga las reservaciones del sitio de clientes. Se relee en cada ciclo
     de polling, no solo al cargar: si alguien lo apaga desde otra tablet o
     desde su teléfono, este panel tiene que enterarse igual. */
  function renderBookingToggle() {
    const label = tabletI18n.t(bookingEnabled ? "booking.on" : "booking.off");
    bookingToggleLabel.textContent = label;
    // El rótulo se esconde en pantallas estrechas, así que el nombre
    // accesible del botón va también en aria-label.
    bookingToggle.setAttribute("aria-label", label);
    bookingToggle.setAttribute("aria-pressed", String(!bookingEnabled));
    bookingToggle.classList.toggle("is-off", !bookingEnabled);
    bookingBanner.hidden = bookingEnabled;
  }

  async function fetchBookingState() {
    try {
      const res = await fetch("/api/settings", { cache: "no-store" });
      if (!res.ok) throw new Error("bad status");
      const data = await res.json();
      bookingEnabled = data.bookingEnabled !== false;
      renderBookingToggle();
    } catch (err) {
      // Falla silenciosa: se reintenta en el próximo ciclo de polling.
    }
  }

  async function toggleBooking() {
    const next = !bookingEnabled;
    // Se pregunta porque es un botón que cambia lo que ve el público, y en
    // una tablet de salón un roce basta para tocarlo.
    const pregunta = tabletI18n.t(next ? "booking.confirmOn" : "booking.confirmOff");
    if (!window.confirm(pregunta)) return;

    bookingToggle.disabled = true;
    try {
      const res = await fetch("/api/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bookingEnabled: next }),
      });
      if (!res.ok) throw new Error("update failed");
      const data = await res.json();
      bookingEnabled = data.bookingEnabled !== false;
      renderBookingToggle();
      showToast(tabletI18n.t(bookingEnabled ? "booking.turnedOn" : "booking.turnedOff"));
    } catch (err) {
      showToast(tabletI18n.t("booking.failed"));
    } finally {
      bookingToggle.disabled = false;
    }
  }

  bookingToggle.addEventListener("click", toggleBooking);

  viewTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      viewTabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      currentView = tab.getAttribute("data-view");
      reservationsView.hidden = currentView !== "reservations";
      tablesView.hidden = currentView !== "tables";
      if (currentView === "tables") fetchTables();
    });
  });

  function applyFilters() {
    const today = todayIso();
    let filtered = reservations.filter((r) => {
      if (dateFilter === "today") return r.date === today;
      if (dateFilter === "upcoming") return r.date >= today;
      return true; // all
    });

    filtered = filtered.filter((r) => {
      if (statusFilter === "active") return !["completed", "cancelled"].includes(r.status);
      if (statusFilter === "needs-call") {
        return (
          r.attendanceReminderSent &&
          r.attendanceConfirmed === null &&
          !["completed", "cancelled"].includes(r.status)
        );
      }
      return r.status === statusFilter;
    });

    filtered.sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time));
    return filtered;
  }

  function render() {
    const filtered = applyFilters();

    let totalGuests = 0;
    filtered.forEach((r) => (totalGuests += r.partySize));
    statTotal.textContent = filtered.length;
    statGuests.textContent = totalGuests;

    if (filtered.length === 0) {
      emptyState.style.display = "block";
      listEl.innerHTML = "";
      return;
    }
    emptyState.style.display = "none";

    let html = "";
    let lastDate = null;
    for (const r of filtered) {
      if (r.date !== lastDate && dateFilter !== "today") {
        html += `<div class="day-heading">${escapeHtml(formatDayHeading(r.date))}</div>`;
        lastDate = r.date;
      }
      html += renderCard(r);
    }
    listEl.innerHTML = html;
    attachActionHandlers();
  }

  function renderAttendanceLine(r) {
    if (r.attendanceConfirmed === true) {
      return `<div class="res-attendance res-attendance-ok">${icon("people")}<span>${escapeHtml(tabletI18n.t("attendance.confirmed"))}</span></div>`;
    }
    if (r.attendanceReminderSent && r.attendanceConfirmed === null && !["completed", "cancelled"].includes(r.status)) {
      return `<div class="res-attendance res-attendance-pending">${icon("clock")}<span>${escapeHtml(tabletI18n.t("attendance.waiting"))}</span></div>`;
    }
    return "";
  }

  function renderCard(r) {
    const badgeClass = `badge-${r.status}`;
    const badgeLabel = tabletI18n.t(`status.${r.status}`);

    let actions = "";
    if (r.status === "pending") {
      actions += `<button class="action-btn action-confirm" data-id="${escapeAttr(r.id)}" data-status="confirmed">${escapeHtml(tabletI18n.t("actions.confirm"))}</button>`;
    }
    if (r.status === "confirmed") {
      actions += `<button class="action-btn action-seat" data-id="${escapeAttr(r.id)}" data-status="seated">${escapeHtml(tabletI18n.t("actions.seat"))}</button>`;
    }
    if (r.status === "seated") {
      actions += `<button class="action-btn action-complete" data-id="${escapeAttr(r.id)}" data-status="completed">${escapeHtml(tabletI18n.t("actions.complete"))}</button>`;
    }
    if (!["completed", "cancelled"].includes(r.status)) {
      actions += `<button class="action-btn action-cancel" data-id="${escapeAttr(r.id)}" data-status="cancelled">${escapeHtml(tabletI18n.t("actions.cancel"))}</button>`;
    }

    return `
      <div class="res-card status-${escapeHtml(r.status)}" data-id="${escapeAttr(r.id)}">
        <div class="res-time">
          <span class="t">${escapeHtml(tabletI18n.formatTime(r.time))}</span>
          <span class="party">${icon("people")}${escapeHtml(String(r.partySize))}</span>
        </div>
        <div class="res-info">
          <div class="res-name">${escapeHtml(r.name)}
            <span class="badge ${badgeClass}">${escapeHtml(badgeLabel)}</span>
          </div>
          <div class="res-sub">
            <span>${icon("phone")}${escapeHtml(r.phone)}</span>
            ${r.email ? `<span>${icon("mail")}${escapeHtml(r.email)}</span>` : ""}
            <span>${icon("hash")}${escapeHtml(String(r.id).slice(0, 8))}</span>
          </div>
          ${r.notes ? `<div class="res-notes">${icon("note")}<span>${escapeHtml(r.notes)}</span></div>` : ""}
          ${renderAttendanceLine(r)}
        </div>
        <div class="res-actions">${actions}</div>
      </div>
    `;
  }

  async function updateStatus(id, status) {
    try {
      const res = await fetch(`/api/reservations/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error("update failed");
      const updated = await res.json();
      const idx = reservations.findIndex((r) => r.id === id);
      if (idx !== -1) reservations[idx] = updated;
      render();
    } catch (err) {
      showToast(tabletI18n.t("toast.updateFailed"));
    }
  }

  function attachActionHandlers() {
    listEl.querySelectorAll(".action-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-id");
        const status = btn.getAttribute("data-status");
        updateStatus(id, status);
      });
    });
  }

  dateTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      dateTabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      dateFilter = tab.getAttribute("data-filter");
      render();
    });
  });

  statusTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      statusTabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      statusFilter = tab.getAttribute("data-status");
      render();
    });
  });

  refreshBtn.addEventListener("click", () => {
    fetchReservations();
    fetchBookingState();
    if (currentView === "tables") fetchTables();
  });

  /* ---------- alta rápida de reserva ----------
     Para cuando entra una llamada: el encargado apunta la mesa sin salir de
     la lista del turno. Usa el mismo endpoint que el formulario público, así
     que pasa por las mismas validaciones y por el control de asientos -- una
     reserva tomada por teléfono no puede saltarse el aforo. */
  const newResBtn = document.getElementById("new-res-btn");
  const newResPopover = document.getElementById("new-res-popover");
  const newResForm = document.getElementById("new-res-form");
  const newResAlert = document.getElementById("new-res-alert");
  const newResSave = document.getElementById("new-res-save");
  const newResCancel = document.getElementById("new-res-cancel");

  function closeNewRes({ devolverFoco = true } = {}) {
    newResPopover.hidden = true;
    newResBtn.setAttribute("aria-expanded", "false");
    newResAlert.hidden = true;
    if (devolverFoco) newResBtn.focus();
  }

  /* Horario del local y hora de pared del restaurante, según el servidor (el
     dispositivo del panel podría tener otra zona horaria). La lista de horas
     ofrece solo las reservables: desde la apertura hasta 15 minutos antes del
     cierre, cada 15 minutos. Para hoy se admiten las de hasta 30 minutos
     atrás (alguien que acaba de sentarse), igual que el servidor. */
  const SLOT_MINUTES = 15;
  const PAST_GRACE_MINUTES = 30;
  let restaurantInfo = null;
  let restaurantClock = null; // { iso: "AAAA-MM-DDTHH:MM", readAt: ms }
  const DAY_KEYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
  const pad2 = (n) => String(n).padStart(2, "0");
  const toMinutes = (hhmm) => {
    const [h, m] = hhmm.split(":").map(Number);
    return h * 60 + m;
  };
  const fromMinutes = (total) => `${pad2(Math.floor(total / 60))}:${pad2(total % 60)}`;

  function loadRestaurantInfo() {
    return fetch("/api/restaurant", { cache: "no-store" })
      .then((r) => r.json())
      .then((d) => {
        restaurantInfo = d;
        if (d.now) restaurantClock = { iso: d.now, readAt: Date.now() };
      })
      .catch(() => {});
  }

  function restaurantNow() {
    if (!restaurantClock) return null;
    const [datePart, timePart] = restaurantClock.iso.split("T");
    const [y, mo, d] = datePart.split("-").map(Number);
    const [h, mi] = timePart.split(":").map(Number);
    const t = new Date(Date.UTC(y, mo - 1, d, h, mi) + (Date.now() - restaurantClock.readAt));
    return {
      date: `${t.getUTCFullYear()}-${pad2(t.getUTCMonth() + 1)}-${pad2(t.getUTCDate())}`,
      minutes: t.getUTCHours() * 60 + t.getUTCMinutes(),
    };
  }

  function fillTimeOptions() {
    const select = newResForm.elements.time;
    const previous = select.value;
    const iso = newResForm.elements.date.value;
    let options = [];
    if (restaurantInfo && restaurantInfo.hours && iso) {
      const [y, m, d] = iso.split("-").map(Number);
      const dayHours = restaurantInfo.hours[DAY_KEYS[new Date(y, m - 1, d).getDay()]];
      if (dayHours) {
        const start = toMinutes(dayHours.open);
        const end = toMinutes(dayHours.close) - restaurantInfo.lastSeatingBufferMinutes;
        const now = restaurantNow();
        for (let t = start; t <= end; t += SLOT_MINUTES) {
          if (now && now.date === iso && t < now.minutes - PAST_GRACE_MINUTES) continue;
          options.push(fromMinutes(t));
        }
      }
    }
    const placeholder = tabletI18n.t(options.length || !iso ? "newRes.timeSelect" : "newRes.noTimes");
    select.innerHTML =
      `<option value="">${escapeHtml(placeholder)}</option>` +
      options.map((v) => `<option value="${v}">${escapeHtml(tabletI18n.formatTime(v))}</option>`).join("");
    if (options.includes(previous)) select.value = previous;
    return options;
  }

  function openNewRes() {
    newResForm.reset();
    newResAlert.hidden = true;
    const now = restaurantNow();
    const hoy = now ? now.date : todayIso();
    newResForm.elements.date.value = hoy;
    newResForm.elements.date.min = hoy;

    // Se propone la próxima franja de cuarto de hora, porque la mayoría de
    // las llamadas son para dentro de un rato. Si hoy ya no queda ninguna
    // (pasada la última reserva), la lista lo avisa y el encargado elige otra fecha.
    const options = fillTimeOptions();
    if (now) {
      const proposal = fromMinutes(Math.ceil((now.minutes + 1) / SLOT_MINUTES) * SLOT_MINUTES);
      if (options.includes(proposal)) newResForm.elements.time.value = proposal;
    }

    newResPopover.hidden = false;
    newResBtn.setAttribute("aria-expanded", "true");
    newResForm.elements.name.focus();
  }

  // Si cambia la fecha, cambian las horas que se pueden elegir (cada día tiene su horario).
  newResForm.elements.date.addEventListener("change", fillTimeOptions);
  document.addEventListener("tablet-languagechange", fillTimeOptions);
  loadRestaurantInfo().then(fillTimeOptions);

  newResBtn.addEventListener("click", () => {
    if (newResPopover.hidden) openNewRes();
    else closeNewRes();
  });

  newResCancel.addEventListener("click", () => closeNewRes());

  // Cerrar al tocar fuera o con Escape, como se espera de un recuadro así.
  document.addEventListener("click", (e) => {
    if (newResPopover.hidden) return;
    if (!e.target.closest(".new-res-wrap")) closeNewRes({ devolverFoco: false });
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !newResPopover.hidden) closeNewRes();
  });

  newResForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = newResForm.elements;
    const payload = {
      name: f.name.value.trim(),
      phone: f.phone.value.trim(),
      date: f.date.value,
      time: f.time.value,
      partySize: Number(f.partySize.value),
      seatingPreference: f.seatingPreference.value,
      notes: f.notes.value.trim(),
    };

    newResSave.disabled = true;
    newResAlert.hidden = true;
    try {
      const res = await fetch("/api/reservations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (!res.ok) {
        const errs = Array.isArray(data.errors) ? data.errors : [];
        newResAlert.textContent = errs
          .map((er) => tabletI18n.t(`errors.${er.code || er}`))
          .join(" · ");
        newResAlert.hidden = false;
        return;
      }

      // La toma el personal por teléfono, así que ya está confirmada: no
      // tiene sentido que aparezca "pendiente" y haya que confirmarla a mano.
      try {
        await fetch(`/api/reservations/${data.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: "confirmed" }),
        });
      } catch (err) {
        /* Si esto falla, la reserva ya existe: se queda pendiente y se
           confirma con un toque desde la lista. No se pierde nada. */
      }

      closeNewRes();
      showToast(tabletI18n.t("newRes.added", { name: data.name }));
      fetchReservations();
      if (currentView === "tables") fetchTables();
    } catch (err) {
      newResAlert.textContent = tabletI18n.t("newRes.failed");
      newResAlert.hidden = false;
    } finally {
      newResSave.disabled = false;
    }
  });

  renderBookingToggle();
  updateClock();
  setInterval(updateClock, 30000);

  fetchReservations();
  fetchBookingState();
  pollTimer = setInterval(() => {
    fetchReservations();
    fetchBookingState();
    if (currentView === "tables") fetchTables();
  }, 5000);
})();

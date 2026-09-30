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
  const tablesGroups = document.getElementById("tables-groups");

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
    dish: "M4 11h16a8 8 0 0 1-16 0M12 4v3M5.5 20h13",
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
  let totalSeats = 0;
  let availableSeats = 0;

  tabletI18n.applyStaticTranslations();

  langSwitcher.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-lang]");
    if (!btn) return;
    tabletI18n.setLang(btn.getAttribute("data-lang"));
  });

  document.addEventListener("tablet-languagechange", () => {
    updateClock();
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

  const TABLE_GROUP_ORDER = ["square4", "rect4", "rect6", "rect12", "rect10"];

  function groupKeyFor(t) {
    return `${t.shape}${t.seats}`;
  }

  async function fetchTables() {
    try {
      const res = await fetch("/api/tables", { cache: "no-store" });
      if (!res.ok) throw new Error("bad status");
      const data = await res.json();
      tables = data.tables || [];
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

    const groups = {};
    tables.forEach((t) => {
      const key = groupKeyFor(t);
      (groups[key] = groups[key] || []).push(t);
    });

    tablesGroups.innerHTML = TABLE_GROUP_ORDER.filter((key) => groups[key])
      .map((key) => {
        const groupTables = groups[key].sort((a, b) => a.index - b.index);
        const tiles = groupTables
          .map(
            (t) => `
            <button type="button" class="table-tile ${t.unavailable ? "unavailable" : "available"}" data-id="${t.id}">
              <span class="table-tile-num">${escapeHtml(tabletI18n.t("tables.table", { n: t.index }))}</span>
              <span class="table-tile-state">${escapeHtml(
                tabletI18n.t(t.unavailable ? "tables.unavailable" : "tables.available")
              )}</span>
            </button>`
          )
          .join("");
        return `
          <div class="table-group">
            <p class="table-group-title">${escapeHtml(tabletI18n.t(`tables.${key}`))}</p>
            <div class="table-tile-grid">${tiles}</div>
          </div>`;
      })
      .join("");

    tablesGroups.querySelectorAll(".table-tile").forEach((btn) => {
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
      actions += `<button class="action-btn action-confirm" data-id="${r.id}" data-status="confirmed">${escapeHtml(tabletI18n.t("actions.confirm"))}</button>`;
    }
    if (r.status === "confirmed") {
      actions += `<button class="action-btn action-seat" data-id="${r.id}" data-status="seated">${escapeHtml(tabletI18n.t("actions.seat"))}</button>`;
    }
    if (r.status === "seated") {
      actions += `<button class="action-btn action-complete" data-id="${r.id}" data-status="completed">${escapeHtml(tabletI18n.t("actions.complete"))}</button>`;
    }
    if (!["completed", "cancelled"].includes(r.status)) {
      actions += `<button class="action-btn action-cancel" data-id="${r.id}" data-status="cancelled">${escapeHtml(tabletI18n.t("actions.cancel"))}</button>`;
    }

    return `
      <div class="res-card status-${escapeHtml(r.status)}" data-id="${r.id}">
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
            <span>${icon("hash")}${escapeHtml(r.id)}</span>
          </div>
          ${r.notes ? `<div class="res-notes">${icon("note")}<span>${escapeHtml(r.notes)}</span></div>` : ""}
          ${
            r.preOrder && r.preOrder.length
              ? `<div class="res-preorder">${icon("dish")}<span>${r.preOrder
                  .map((i) => `${i.quantity}× ${escapeHtml(i.name)}`)
                  .join(", ")}</span></div>`
              : ""
          }
          ${r.preOrderNotes ? `<div class="res-notes">${icon("dish")}<span>${escapeHtml(r.preOrderNotes)}</span></div>` : ""}
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
    if (currentView === "tables") fetchTables();
  });

  updateClock();
  setInterval(updateClock, 30000);

  fetchReservations();
  pollTimer = setInterval(() => {
    fetchReservations();
    if (currentView === "tables") fetchTables();
  }, 5000);
})();

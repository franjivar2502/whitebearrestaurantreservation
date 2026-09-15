(function () {
  const listEl = document.getElementById("reservation-list");
  const emptyState = document.getElementById("empty-state");
  const statTotal = document.getElementById("stat-total");
  const statGuests = document.getElementById("stat-guests");
  const clockEl = document.getElementById("clock");
  const toastEl = document.getElementById("toast");
  const refreshBtn = document.getElementById("refresh-btn");

  const dateTabs = document.querySelectorAll(".tab[data-filter]");
  const statusTabs = document.querySelectorAll(".tab[data-status]");

  let dateFilter = "today"; // today | upcoming | all
  let statusFilter = "active"; // active | pending | confirmed
  let reservations = [];
  let pollTimer = null;
  let lastSeenIds = new Set();
  let firstLoad = true;

  const STATUS_LABELS = {
    pending: "Pendiente",
    confirmed: "Confirmada",
    seated: "Sentados",
    completed: "Finalizada",
    cancelled: "Cancelada",
  };

  function todayIso() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  function updateClock() {
    const now = new Date();
    clockEl.textContent =
      now.toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" }) +
      " · " +
      now.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
  }

  function formatTime(hhmm) {
    const [h, m] = hhmm.split(":").map(Number);
    const d = new Date();
    d.setHours(h, m, 0, 0);
    return d.toLocaleTimeString("es-ES", { hour: "numeric", minute: "2-digit" });
  }

  function formatDayHeading(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    const date = new Date(y, m - 1, d);
    const isToday = iso === todayIso();
    const label = date.toLocaleDateString("es-ES", {
      weekday: "long",
      day: "numeric",
      month: "long",
    });
    return isToday ? `Hoy · ${label}` : label;
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
              ? `Nueva reservación: ${newOnes[0].name}`
              : `${newOnes.length} nuevas reservaciones`
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

  function applyFilters() {
    const today = todayIso();
    let filtered = reservations.filter((r) => {
      if (dateFilter === "today") return r.date === today;
      if (dateFilter === "upcoming") return r.date >= today;
      return true; // all
    });

    filtered = filtered.filter((r) => {
      if (statusFilter === "active") return !["completed", "cancelled"].includes(r.status);
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

  function renderCard(r) {
    const badgeClass = `badge-${r.status}`;
    const badgeLabel = STATUS_LABELS[r.status] || r.status;

    let actions = "";
    if (r.status === "pending") {
      actions += `<button class="action-btn action-confirm" data-id="${r.id}" data-status="confirmed">Confirmar</button>`;
    }
    if (r.status === "confirmed") {
      actions += `<button class="action-btn action-seat" data-id="${r.id}" data-status="seated">Sentar</button>`;
    }
    if (r.status === "seated") {
      actions += `<button class="action-btn action-complete" data-id="${r.id}" data-status="completed">Finalizar</button>`;
    }
    if (!["completed", "cancelled"].includes(r.status)) {
      actions += `<button class="action-btn action-cancel" data-id="${r.id}" data-status="cancelled">Cancelar</button>`;
    }

    return `
      <div class="res-card" data-id="${r.id}">
        <div class="res-time">
          <span class="t">${escapeHtml(formatTime(r.time))}</span>
          <span class="party">👥 ${escapeHtml(String(r.partySize))}</span>
        </div>
        <div class="res-info">
          <div class="res-name">${escapeHtml(r.name)}
            <span class="badge ${badgeClass}">${escapeHtml(badgeLabel)}</span>
          </div>
          <div class="res-sub">
            <span>📞 ${escapeHtml(r.phone)}</span>
            ${r.email ? `<span>✉️ ${escapeHtml(r.email)}</span>` : ""}
            <span>#${escapeHtml(r.id)}</span>
          </div>
          ${r.notes ? `<div class="res-notes">📝 ${escapeHtml(r.notes)}</div>` : ""}
          ${
            r.preOrder && r.preOrder.length
              ? `<div class="res-preorder">🍽️ Preorden: ${r.preOrder
                  .map((i) => `${i.quantity}× ${escapeHtml(i.name)}`)
                  .join(", ")}</div>`
              : ""
          }
          ${r.preOrderNotes ? `<div class="res-notes">🍽️ ${escapeHtml(r.preOrderNotes)}</div>` : ""}
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
      showToast("No se pudo actualizar la reservación.");
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

  refreshBtn.addEventListener("click", fetchReservations);

  updateClock();
  setInterval(updateClock, 30000);

  fetchReservations();
  pollTimer = setInterval(fetchReservations, 5000);
})();

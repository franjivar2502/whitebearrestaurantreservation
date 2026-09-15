(function () {
  const form = document.getElementById("reservation-form");
  const alertBox = document.getElementById("form-alert");
  const submitBtn = document.getElementById("submit-btn");
  const confirmation = document.getElementById("confirmation");
  const confirmationDetails = document.getElementById("confirmation-details");
  const newReservationBtn = document.getElementById("new-reservation-btn");
  const dateInput = document.getElementById("date");
  const timeInput = document.getElementById("time");
  const timeHint = document.getElementById("time-hint");
  const heroHours = document.getElementById("hero-hours");
  const partySizeInput = document.getElementById("partySize");
  const groupMenuSection = document.getElementById("group-menu-section");
  const groupMenuNote = document.getElementById("group-menu-note");
  const groupMenuItemsEl = document.getElementById("group-menu-items");
  const preOrderNotesInput = document.getElementById("preOrderNotes");
  const infoToggleBtn = document.getElementById("info-toggle-btn");
  const infoContent = document.getElementById("info-content");

  infoToggleBtn.addEventListener("click", () => {
    const expanded = infoToggleBtn.getAttribute("aria-expanded") === "true";
    infoToggleBtn.setAttribute("aria-expanded", String(!expanded));
    infoContent.hidden = expanded;
    infoToggleBtn.textContent = expanded ? "Ver todo ▾" : "Ver menos ▴";
  });

  // No permitir seleccionar fechas pasadas
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, "0");
  const dd = String(today.getDate()).padStart(2, "0");
  dateInput.min = `${yyyy}-${mm}-${dd}`;
  if (!dateInput.value) dateInput.value = `${yyyy}-${mm}-${dd}`;

  const DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
  const DAY_LABELS = {
    mon: "Lunes",
    tue: "Martes",
    wed: "Miércoles",
    thu: "Jueves",
    fri: "Viernes",
    sat: "Sábado",
    sun: "Domingo",
  };

  // Respaldo por si /api/restaurant no responde.
  let restaurantInfo = {
    hours: {
      mon: { open: "11:00", close: "21:00" },
      tue: { open: "11:00", close: "21:00" },
      wed: { open: "11:00", close: "21:00" },
      thu: { open: "11:00", close: "21:00" },
      fri: { open: "11:00", close: "21:30" },
      sat: { open: "11:00", close: "21:30" },
      sun: { open: "11:00", close: "21:00" },
    },
    lastSeatingBufferMinutes: 30,
    groupMenu: { threshold: 20, note: "", items: [] },
  };

  const menuQuantities = {}; // itemId -> cantidad

  function showAlert(messages) {
    alertBox.innerHTML = "";
    const div = document.createElement("div");
    div.className = "alert alert-error";
    div.innerHTML = messages.map((m) => `• ${escapeHtml(m)}`).join("<br/>");
    alertBox.appendChild(div);
    div.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function clearAlert() {
    alertBox.innerHTML = "";
  }

  function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }

  function formatDate(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    const date = new Date(y, m - 1, d);
    return date.toLocaleDateString("es-ES", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }

  function formatTime(hhmm) {
    const [h, m] = hhmm.split(":").map(Number);
    const period = h < 12 ? "a.m." : "p.m.";
    let h12 = h % 12;
    if (h12 === 0) h12 = 12;
    return `${h12}:${String(m).padStart(2, "0")} ${period}`;
  }

  function dayKeyForDate(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    const date = new Date(y, m - 1, d);
    return DAY_ORDER[(date.getDay() + 6) % 7]; // getDay(): dom=0..sáb=6 -> lun=0..dom=6
  }

  function subtractMinutes(hhmm, minutes) {
    const [h, m] = hhmm.split(":").map(Number);
    let total = h * 60 + m - minutes;
    total = Math.max(total, 0);
    const hh = String(Math.floor(total / 60)).padStart(2, "0");
    const mm2 = String(total % 60).padStart(2, "0");
    return `${hh}:${mm2}`;
  }

  function renderHeroHours() {
    const groups = [];
    for (const key of DAY_ORDER) {
      const h = restaurantInfo.hours[key];
      const last = groups[groups.length - 1];
      if (last && last.open === h.open && last.close === h.close) {
        last.days.push(key);
      } else {
        groups.push({ open: h.open, close: h.close, days: [key] });
      }
    }
    const lines = groups.map((g) => {
      let label;
      if (g.days.length === 1) {
        label = DAY_LABELS[g.days[0]];
      } else if (g.days.length === 2) {
        label = `${DAY_LABELS[g.days[0]]} y ${DAY_LABELS[g.days[1]]}`;
      } else {
        label = `${DAY_LABELS[g.days[0]]} a ${DAY_LABELS[g.days[g.days.length - 1]]}`;
      }
      return `${label}: ${formatTime(g.open)} – ${formatTime(g.close)}`;
    });
    heroHours.innerHTML = lines
      .map((line, i) => `<span>${i === 0 ? "🕒 " : "&nbsp;&nbsp;&nbsp;&nbsp;"}${escapeHtml(line)}</span>`)
      .join("");
  }

  function updateTimeConstraints() {
    const dayKey = dayKeyForDate(dateInput.value);
    const dayHours = restaurantInfo.hours[dayKey];
    const lastSeating = subtractMinutes(dayHours.close, restaurantInfo.lastSeatingBufferMinutes);
    timeInput.min = dayHours.open;
    timeInput.max = lastSeating;
    timeHint.textContent = `${DAY_LABELS[dayKey]}: reservaciones de ${formatTime(dayHours.open)} a ${formatTime(lastSeating)}`;
  }

  dateInput.addEventListener("change", updateTimeConstraints);

  function renderGroupMenu() {
    const menu = restaurantInfo.groupMenu;
    groupMenuNote.textContent = menu.note || "";

    if (!menu.items.length) {
      groupMenuItemsEl.innerHTML = `<p class="hint">El menú de grupo aún no está disponible; el staff te ayudará a definir el pedido al llegar.</p>`;
      return;
    }

    groupMenuItemsEl.innerHTML = menu.items
      .map(
        (item) => `
        <div class="menu-item-row" data-item-id="${escapeHtml(item.id)}">
          <div class="menu-item-info">
            <div class="menu-item-name">${escapeHtml(item.name)}</div>
            ${item.description ? `<div class="menu-item-desc">${escapeHtml(item.description)}</div>` : ""}
          </div>
          <div class="qty-stepper">
            <button type="button" class="qty-btn" data-action="dec" aria-label="Quitar uno">−</button>
            <span class="qty-value" data-qty-value>${menuQuantities[item.id] || 0}</span>
            <button type="button" class="qty-btn" data-action="inc" aria-label="Agregar uno">+</button>
          </div>
        </div>`
      )
      .join("");

    groupMenuItemsEl.querySelectorAll(".menu-item-row").forEach((row) => {
      const itemId = row.getAttribute("data-item-id");
      const valueEl = row.querySelector("[data-qty-value]");
      row.querySelectorAll(".qty-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          const current = menuQuantities[itemId] || 0;
          const next =
            btn.getAttribute("data-action") === "inc" ? current + 1 : Math.max(0, current - 1);
          menuQuantities[itemId] = next;
          valueEl.textContent = next;
        });
      });
    });
  }

  function updateGroupMenuVisibility() {
    const size = parseInt(partySizeInput.value, 10) || 0;
    const shouldShow = size >= restaurantInfo.groupMenu.threshold;
    groupMenuSection.hidden = !shouldShow;
  }

  partySizeInput.addEventListener("input", updateGroupMenuVisibility);

  fetch("/api/restaurant")
    .then((res) => res.json())
    .then((data) => {
      if (data && data.hours) restaurantInfo = data;
    })
    .catch(() => {})
    .finally(() => {
      renderHeroHours();
      updateTimeConstraints();
      renderGroupMenu();
      updateGroupMenuVisibility();
    });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlert();
    submitBtn.disabled = true;
    submitBtn.textContent = "Enviando...";

    const preOrder = groupMenuSection.hidden
      ? []
      : Object.entries(menuQuantities)
          .filter(([, qty]) => qty > 0)
          .map(([itemId, qty]) => ({ itemId, quantity: qty }));

    const payload = {
      name: form.name.value,
      phone: form.phone.value,
      email: form.email.value,
      date: form.date.value,
      time: form.time.value,
      partySize: form.partySize.value,
      notes: [
        form.occasion.value ? `Ocasión: ${form.occasion.value}.` : "",
        form.notes.value.trim(),
      ]
        .filter(Boolean)
        .join(" "),
      preOrder,
      preOrderNotes: groupMenuSection.hidden ? "" : preOrderNotesInput.value.trim(),
    };

    try {
      const res = await fetch("/api/reservations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (!res.ok) {
        showAlert(data.errors || ["Ocurrió un error. Intenta de nuevo."]);
        submitBtn.disabled = false;
        submitBtn.textContent = "Reservar mesa";
        return;
      }

      confirmationDetails.innerHTML = `
        <dt>Nombre</dt><dd>${escapeHtml(data.name)}</dd>
        <dt>Fecha</dt><dd>${escapeHtml(formatDate(data.date))}</dd>
        <dt>Hora</dt><dd>${escapeHtml(formatTime(data.time))}</dd>
        <dt>Personas</dt><dd>${escapeHtml(String(data.partySize))}</dd>
        <dt>Teléfono</dt><dd>${escapeHtml(data.phone)}</dd>
        ${data.email ? `<dt>Correo</dt><dd>${escapeHtml(data.email)}</dd>` : ""}
        <dt>Código</dt><dd>#${escapeHtml(data.id)}</dd>
        ${
          data.preOrder && data.preOrder.length
            ? `<dt>Preorden</dt><dd>${data.preOrder
                .map((i) => `${i.quantity}× ${escapeHtml(i.name)}`)
                .join(", ")}</dd>`
            : ""
        }
      `;
      form.style.display = "none";
      confirmation.style.display = "block";
      confirmation.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      showAlert(["No se pudo conectar con el servidor. Intenta de nuevo."]);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Reservar mesa";
    }
  });

  newReservationBtn.addEventListener("click", () => {
    form.reset();
    dateInput.value = `${yyyy}-${mm}-${dd}`;
    Object.keys(menuQuantities).forEach((key) => delete menuQuantities[key]);
    renderGroupMenu();
    updateGroupMenuVisibility();
    form.style.display = "block";
    confirmation.style.display = "none";
    clearAlert();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
})();

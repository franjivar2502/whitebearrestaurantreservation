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
  const partySizeHint = document.getElementById("party-size-hint");
  const groupMenuSection = document.getElementById("group-menu-section");
  const groupMenuNote = document.getElementById("group-menu-note");
  const groupMenuItemsEl = document.getElementById("group-menu-items");
  const preOrderNotesInput = document.getElementById("preOrderNotes");
  const infoHeader = document.getElementById("info-header");
  const infoToggleBtn = document.getElementById("info-toggle-btn");
  const infoContent = document.getElementById("info-content");
  const aboutHeader = document.getElementById("about-header");
  const aboutToggleBtn = document.getElementById("about-toggle-btn");
  const aboutContent = document.getElementById("about-content");
  const galleryHeader = document.getElementById("gallery-header");
  const galleryToggleBtn = document.getElementById("gallery-toggle-btn");
  const mapCard = document.getElementById("map-card");
  const mapHeader = document.getElementById("map-header");
  const mapToggleBtn = document.getElementById("map-toggle-btn");
  const mapEmbed = document.getElementById("map-embed");
  const langSwitcher = document.getElementById("lang-switcher");
  const welcomeSplash = document.getElementById("welcome-splash");

  // Barras desplegables (About us, Venue information, Gallery, Find us):
  // un mismo patrón de clic-para-expandir/contraer para las cuatro.
  function makeCollapsible(header, toggleBtn, content, onToggle) {
    let expanded = false;
    function render() {
      toggleBtn.textContent = i18n.t(expanded ? "info.seeLess" : "info.seeAll");
    }
    header.addEventListener("click", () => {
      expanded = !expanded;
      toggleBtn.setAttribute("aria-expanded", String(expanded));
      content.hidden = !expanded;
      if (onToggle) onToggle(expanded);
      render();
    });
    return render;
  }

  const DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

  i18n.applyStaticTranslations();

  // Pantalla de bienvenida (si hay fotos, muestra la primera como fondo
  // durante 1 segundo) y galería visible en la página.
  const galleryCard = document.getElementById("gallery-card");
  const photoGallery = document.getElementById("photo-gallery");

  const hideWelcomeSplash = () => {
    setTimeout(() => {
      welcomeSplash.classList.add("welcome-splash-hide");
      setTimeout(() => {
        welcomeSplash.hidden = true;
      }, 650);
    }, 1000);
  };

  welcomeSplash.hidden = false;

  fetch("/api/photos")
    .then((res) => res.json())
    .then((photos) => {
      if (photos && photos.length) {
        welcomeSplash.style.backgroundImage = `url("${photos[0].url}")`;
        galleryCard.hidden = false;
        photoGallery.innerHTML = photos
          .map((p) => `<img src="${p.url}" alt="${(p.caption || "").replace(/"/g, "&quot;")}" loading="lazy">`)
          .join("");
      }
      hideWelcomeSplash();
    })
    .catch(() => hideWelcomeSplash());

  langSwitcher.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-lang]");
    if (!btn) return;
    i18n.setLang(btn.getAttribute("data-lang"));
  });

  const renderInfoToggleLabel = makeCollapsible(infoHeader, infoToggleBtn, infoContent);
  const renderAboutToggleLabel = makeCollapsible(aboutHeader, aboutToggleBtn, aboutContent);
  const renderGalleryToggleLabel = makeCollapsible(galleryHeader, galleryToggleBtn, photoGallery);
  const renderMapToggleLabel = makeCollapsible(mapHeader, mapToggleBtn, mapEmbed, (expanded) => {
    mapCard.classList.toggle("expanded", expanded);
  });

  function renderInfoSection() {
    const groups = i18n.getInfoGroups();
    infoContent.innerHTML = Object.values(groups)
      .map(
        (group) => `
        <div>
          <p class="info-group-title">${escapeHtml(group.title)}</p>
          <div class="info-chips">
            ${group.items.map((item) => `<span class="highlight-chip">${escapeHtml(item)}</span>`).join("")}
          </div>
        </div>`
      )
      .join("");
  }

  // No permitir seleccionar fechas pasadas
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, "0");
  const dd = String(today.getDate()).padStart(2, "0");
  dateInput.min = `${yyyy}-${mm}-${dd}`;
  if (!dateInput.value) dateInput.value = `${yyyy}-${mm}-${dd}`;

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
    maxPartySize: 40,
    phone: "(518) 302-5235",
    groupMenu: { threshold: 20, items: [] },
  };

  const menuQuantities = {}; // itemId -> cantidad

  function showAlert(errors) {
    alertBox.innerHTML = "";
    const messages = (errors || [{ code: "GENERIC" }]).map((err) => {
      if (typeof err === "string") return err; // por si el servidor devuelve texto plano
      return i18n.t(`errors.${err.code}`, err.params);
    });
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
    d.textContent = str == null ? "" : str;
    return d.innerHTML;
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
        label = i18n.dayName(g.days[0]);
      } else if (g.days.length === 2) {
        label = `${i18n.dayName(g.days[0])} ${i18n.joinWord("pair")} ${i18n.dayName(g.days[1])}`;
      } else {
        label = `${i18n.dayName(g.days[0])} ${i18n.joinWord("range")} ${i18n.dayName(g.days[g.days.length - 1])}`;
      }
      return `${label}: ${i18n.formatTime(g.open)} – ${i18n.formatTime(g.close)}`;
    });
    heroHours.innerHTML = lines
      .map((line, i) => `<span>${i === 0 ? "🕒 " : "&nbsp;&nbsp;&nbsp;&nbsp;"}${escapeHtml(line)}</span>`)
      .join("");
  }

  function updateTimeConstraints() {
    const dayKey = i18n.dayKeyForDate(dateInput.value);
    const dayHours = restaurantInfo.hours[dayKey];
    const lastSeating = subtractMinutes(dayHours.close, restaurantInfo.lastSeatingBufferMinutes);
    timeInput.min = dayHours.open;
    timeInput.max = lastSeating;
    timeHint.textContent = i18n.t("form.timeHint", {
      day: i18n.dayName(dayKey),
      open: i18n.formatTime(dayHours.open),
      close: i18n.formatTime(lastSeating),
    });
  }

  dateInput.addEventListener("change", updateTimeConstraints);

  function renderGroupMenu() {
    const menu = restaurantInfo.groupMenu;
    groupMenuNote.textContent = i18n.t("groupMenu.note", { threshold: menu.threshold });

    if (!menu.items.length) {
      groupMenuItemsEl.innerHTML = `<p class="hint">${escapeHtml(i18n.t("groupMenu.emptyMenu"))}</p>`;
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
            <button type="button" class="qty-btn" data-action="dec">−</button>
            <span class="qty-value" data-qty-value>${menuQuantities[item.id] || 0}</span>
            <button type="button" class="qty-btn" data-action="inc">+</button>
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

  function renderPartySizeHint() {
    partySizeHint.textContent = i18n.t("form.partySizeHint", {
      max: restaurantInfo.maxPartySize,
      phone: restaurantInfo.phone,
    });
  }

  partySizeInput.addEventListener("input", updateGroupMenuVisibility);

  function renderAll() {
    renderInfoSection();
    renderInfoToggleLabel();
    renderAboutToggleLabel();
    renderGalleryToggleLabel();
    renderMapToggleLabel();
    renderHeroHours();
    updateTimeConstraints();
    renderPartySizeHint();
    renderGroupMenu();
    updateGroupMenuVisibility();
  }

  document.addEventListener("languagechange", renderAll);

  fetch("/api/restaurant")
    .then((res) => res.json())
    .then((data) => {
      if (data && data.hours) restaurantInfo = data;
    })
    .catch(() => {})
    .finally(renderAll);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlert();
    submitBtn.disabled = true;
    submitBtn.classList.add("btn-loading");
    submitBtn.textContent = i18n.t("form.submitting");

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
      notes: [form.occasion.value ? `Occasion: ${form.occasion.value}.` : "", form.notes.value.trim()]
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
        showAlert(data.errors);
        submitBtn.disabled = false;
        submitBtn.classList.remove("btn-loading");
        submitBtn.textContent = i18n.t("form.submit");
        return;
      }

      confirmationDetails.innerHTML = `
        <dt>${i18n.t("confirmation.name")}</dt><dd>${escapeHtml(data.name)}</dd>
        <dt>${i18n.t("confirmation.date")}</dt><dd>${escapeHtml(i18n.formatDateLong(data.date))}</dd>
        <dt>${i18n.t("confirmation.time")}</dt><dd>${escapeHtml(i18n.formatTime(data.time))}</dd>
        <dt>${i18n.t("confirmation.partySize")}</dt><dd>${escapeHtml(String(data.partySize))}</dd>
        <dt>${i18n.t("confirmation.phone")}</dt><dd>${escapeHtml(data.phone)}</dd>
        ${data.email ? `<dt>${i18n.t("confirmation.email")}</dt><dd>${escapeHtml(data.email)}</dd>` : ""}
        <dt>${i18n.t("confirmation.code")}</dt><dd>#${escapeHtml(data.id)}</dd>
        ${
          data.preOrder && data.preOrder.length
            ? `<dt>${i18n.t("confirmation.preorder")}</dt><dd>${data.preOrder
                .map((i) => `${i.quantity}× ${escapeHtml(i.name)}`)
                .join(", ")}</dd>`
            : ""
        }
      `;
      form.style.display = "none";
      confirmation.style.display = "block";
      confirmation.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      showAlert([{ code: "NETWORK" }]);
    } finally {
      submitBtn.disabled = false;
      submitBtn.classList.remove("btn-loading");
      submitBtn.textContent = i18n.t("form.submit");
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

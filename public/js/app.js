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
  const bookingClosedNotice = document.getElementById("booking-closed-notice");
  const heroHours = document.getElementById("hero-hours");
  const partySizeHint = document.getElementById("party-size-hint");
  const infoHeader = document.getElementById("info-header");
  const infoToggleBtn = document.getElementById("info-toggle-btn");
  const infoContent = document.getElementById("info-content");
  const menuGalleryCard = document.getElementById("menu-card");
  const menuGalleryHeader = document.getElementById("menu-header");
  const menuGalleryToggleBtn = document.getElementById("menu-toggle-btn");
  const menuGallery = document.getElementById("menu-gallery");
  const reviewsHeader = document.getElementById("reviews-header");
  const reviewsToggleBtn = document.getElementById("reviews-toggle-btn");
  const reviewsContent = document.getElementById("reviews-content");
  const restaurantInfoHeader = document.getElementById("restaurant-info-header");
  const restaurantInfoToggleBtn = document.getElementById("restaurant-info-toggle-btn");
  const restaurantInfoContent = document.getElementById("restaurant-info-content");
  const reviewsList = document.getElementById("reviews-list");
  const reviewForm = document.getElementById("review-form");
  const reviewAlertBox = document.getElementById("review-alert");
  const reviewSubmitBtn = document.getElementById("review-submit-btn");
  const langSwitcher = document.getElementById("lang-switcher");
  const welcomeSplash = document.getElementById("welcome-splash");

  // Barras desplegables (Venue information, Our Menu, Reviews, Find us):
  // un mismo patrón de clic-para-expandir/contraer para todas.
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
  // durante 1 segundo) y fotos del menú visibles en la página.

  const hideWelcomeSplash = () => {
    setTimeout(() => {
      welcomeSplash.classList.add("welcome-splash-hide");
      setTimeout(() => {
        welcomeSplash.hidden = true;
      }, 650);
    }, 1000);
  };

  welcomeSplash.hidden = false;

  /* La URL va escapada igual que el texto. Antes se interpolaba cruda dentro
     de src="...": una URL con una comilla se salía del atributo y podía meter
     un onerror. El servidor exige que empiece por http:// o https://, pero
     eso no impide que lleve una comilla más adelante. */
  const photoImgTag = (p) =>
    `<img src="${escapeAttr(p.url)}" alt="${escapeAttr(p.caption || "")}" loading="lazy">`;

  /* Carrusel de platos que acompaña al formulario en pantalla ancha.
     Solo arranca si hay fotos de la sección "menu": sin contenido se queda
     oculto y el formulario ocupa todo el ancho, en vez de dejar un hueco. */
  const DISH_RAIL_INTERVAL = 3000;

  function startDishRail(menuPhotos) {
    const rail = document.getElementById("dish-rail");
    const frame = document.getElementById("dish-rail-frame");
    const toggle = document.getElementById("dish-rail-toggle");
    if (!rail || !frame || !menuPhotos.length) return;

    // Orden aleatorio (Fisher-Yates sobre una copia, para no alterar el
    // orden que el staff definió para la galería).
    const shuffled = menuPhotos.slice();
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }

    frame.innerHTML = shuffled
      .map(
        (p, i) =>
          `<img src="${escapeAttr(p.url)}" alt="${escapeAttr(p.caption || "")}"` +
          `${i === 0 ? ' class="is-current"' : ""}` +
          `${i > 1 ? ' loading="lazy"' : ""}>`
      )
      .join("");
    rail.hidden = false;

    const slides = Array.from(frame.children);
    if (slides.length < 2) return; // una sola foto: nada que rotar

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let index = 0;
    let timer = null;
    // Con movimiento reducido el carrusel arranca detenido: se ve la primera
    // foto y quien quiera las demás puede darle al botón.
    let paused = reduceMotion;
    let onScreen = true;

    function step() {
      slides[index].classList.remove("is-current");
      index = (index + 1) % slides.length;
      slides[index].classList.add("is-current");
    }

    function sync() {
      const shouldRun = !paused && onScreen && !document.hidden;
      if (shouldRun && !timer) {
        timer = setInterval(step, DISH_RAIL_INTERVAL);
      } else if (!shouldRun && timer) {
        clearInterval(timer);
        timer = null;
      }
    }

    function setPaused(next) {
      paused = next;
      toggle.setAttribute("aria-pressed", String(paused));
      toggle.innerHTML = paused
        ? '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M7 4.5v15l13-7.5z"/></svg>'
        : '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M9 5v14M15 5v14"/></svg>';
      toggle.setAttribute("title", i18n.t(paused ? "dishRail.play" : "dishRail.pause"));
      toggle.setAttribute("aria-label", toggle.getAttribute("title"));
      sync();
    }

    toggle.addEventListener("click", () => setPaused(!paused));
    setPaused(paused);

    // No gastar batería rotando fotos que nadie está viendo.
    document.addEventListener("visibilitychange", sync);
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(
        (entries) => {
          onScreen = entries[0].isIntersecting;
          sync();
        },
        { threshold: 0.1 }
      ).observe(rail);
    }
  }

  fetch("/api/photos")
    .then((res) => res.json())
    .then((photos) => {
      if (photos && photos.length) {
        const menuPhotos = photos.filter((p) => p.category === "menu");

        if (menuPhotos.length) {
          menuGalleryCard.hidden = false;
          menuGallery.innerHTML = menuPhotos.map(photoImgTag).join("");
        }
        startDishRail(menuPhotos);
      }
      hideWelcomeSplash();
    })
    .catch(() => hideWelcomeSplash());

  fetchReviews();

  langSwitcher.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-lang]");
    if (!btn) return;
    i18n.setLang(btn.getAttribute("data-lang"));
  });

  const renderInfoToggleLabel = makeCollapsible(infoHeader, infoToggleBtn, infoContent);
  const renderMenuGalleryToggleLabel = makeCollapsible(menuGalleryHeader, menuGalleryToggleBtn, menuGallery);
  const renderReviewsToggleLabel = makeCollapsible(reviewsHeader, reviewsToggleBtn, reviewsContent);
  const renderRestaurantInfoToggleLabel = makeCollapsible(
    restaurantInfoHeader,
    restaurantInfoToggleBtn,
    restaurantInfoContent
  );

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
    maxPartySize: 40,
    phone: "(518) 302-5235",
  };

  function showAlert(errors) {
    alertBox.innerHTML = "";
    const messages = (errors || [{ code: "GENERIC" }]).map((err) => {
      if (typeof err === "string") return err; // por si el servidor devuelve texto plano
      return i18n.t(`errors.${err.code}`, { phone: restaurantInfo.phone, ...err.params });
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

  /* Para texto dentro de un atributo hace falta otra cosa que escapeHtml.
     Aquel pasa por textContent/innerHTML, que escapa < y & pero deja pasar
     las comillas -- y la comilla es justo el carácter con el que se sale uno
     de src="..." para colar un onerror. */
  function escapeAttr(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function showFormAlert(box, kind, message) {
    box.innerHTML = "";
    const div = document.createElement("div");
    div.className = `alert alert-${kind}`;
    div.innerHTML = message;
    box.appendChild(div);
  }

  let reviewsCache = [];

  function renderReviewsList() {
    if (!reviewsCache.length) {
      reviewsList.innerHTML = `<p class="hint">${escapeHtml(i18n.t("reviews.empty"))}</p>`;
      return;
    }
    reviewsList.innerHTML = reviewsCache
      .map((r) => {
        const rating = Number(r.rating) || 0;
        const stars = "★".repeat(rating) + "☆".repeat(5 - rating);
        return `
          <div class="review-item">
            <div class="review-item-header">
              <span class="review-stars" aria-hidden="true">${stars}</span>
              <span class="review-name">${escapeHtml(i18n.t("reviews.by", { name: r.name }))}</span>
            </div>
            <p class="review-text">${escapeHtml(r.text)}</p>
            ${r.photoUrl ? `<img class="review-photo" src="${escapeAttr(r.photoUrl)}" alt="" loading="lazy">` : ""}
          </div>`;
      })
      .join("");
  }

  function fetchReviews() {
    fetch("/api/reviews")
      .then((res) => res.json())
      .then((data) => {
        reviewsCache = Array.isArray(data) ? data : [];
        renderReviewsList();
      })
      .catch(() => {});
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

  /* Se reservan mesas a cualquier hora de cualquier día (24/7): el campo de
     hora no lleva min/max. El horario del restaurante se muestra arriba solo
     como información. */
  function updateTimeConstraints() {
    timeInput.removeAttribute("min");
    timeInput.removeAttribute("max");
    timeHint.textContent = i18n.t("form.timeHintAnyTime");
  }

  dateInput.addEventListener("change", updateTimeConstraints);

  /* ---------- agenda abierta / cerrada ----------
     El staff apaga las reservaciones desde su panel. Cuando están apagadas,
     el formulario se deshabilita con un aviso arriba: más honesto que
     dejarlo llenar para devolver un error al enviarlo. */
  function applyBookingState() {
    const open = restaurantInfo.bookingEnabled !== false;
    bookingClosedNotice.textContent = open
      ? ""
      : i18n.t("form.bookingClosed", { phone: restaurantInfo.phone });
    bookingClosedNotice.hidden = open;
    submitBtn.disabled = !open;
    Array.from(form.elements).forEach((el) => {
      if (el !== submitBtn) el.disabled = !open;
    });
  }

  function renderPartySizeHint() {
    partySizeHint.textContent = i18n.t("form.partySizeHint", {
      max: restaurantInfo.maxPartySize,
      phone: restaurantInfo.phone,
    });
  }

  function renderAll() {
    renderInfoSection();
    renderInfoToggleLabel();
    renderMenuGalleryToggleLabel();
    renderReviewsToggleLabel();
    renderRestaurantInfoToggleLabel();
    renderReviewsList();
    renderHeroHours();
    updateTimeConstraints();
    applyBookingState();
    renderPartySizeHint();
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
    // El formulario lleva novalidate, así que la casilla se comprueba aquí.
    if (!form.termsConsent.checked) {
      showAlert([{ code: "CONSENT_REQUIRED" }]);
      return;
    }
    submitBtn.disabled = true;
    submitBtn.classList.add("btn-loading");
    submitBtn.textContent = i18n.t("form.submitting");

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
      seatingPreference: form.seatingPreference.value,
      website: form.website.value,
      termsConsent: form.termsConsent.checked,
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
        // La agenda pudo cerrarse mientras el cliente llenaba el formulario:
        // en ese caso no basta el error, hay que bloquearlo como al cargar.
        if ((data.errors || []).some((er) => er && er.code === "BOOKING_CLOSED")) {
          restaurantInfo.bookingEnabled = false;
          applyBookingState();
          return;
        }
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
        ${
          data.seatingPreference
            ? `<dt>${i18n.t("confirmation.seating")}</dt><dd>${escapeHtml(
                i18n.t(data.seatingPreference === "inside" ? "form.seatingInside" : "form.seatingOutside")
              )}</dd>`
            : ""
        }
        <dt>${i18n.t("confirmation.code")}</dt><dd>#${escapeHtml(String(data.id).slice(0, 8))}</dd>
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

  reviewForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    reviewAlertBox.innerHTML = "";
    if (!reviewForm.reviewConsent.checked) {
      showFormAlert(reviewAlertBox, "error", escapeHtml(i18n.t("errors.REVIEW_CONSENT_REQUIRED")));
      return;
    }
    reviewSubmitBtn.disabled = true;
    reviewSubmitBtn.classList.add("btn-loading");
    reviewSubmitBtn.textContent = i18n.t("reviews.submitting");

    const formData = new FormData(reviewForm);

    try {
      const res = await fetch("/api/reviews", { method: "POST", body: formData });
      const data = await res.json();

      if (!res.ok) {
        const messages = (data.errors || [{ code: "REVIEW_INVALID" }]).map((err) =>
          escapeHtml(i18n.t(`errors.${err.code}`, { ...err.params, phone: restaurantInfo.phone }))
        );
        showFormAlert(reviewAlertBox, "error", messages.map((m) => `• ${m}`).join("<br/>"));
        return;
      }

      reviewForm.reset();
      // Una reseña retenida para el staff no se muestra todavía en la lista.
      if (data.status === "approved") {
        reviewsCache = [data, ...reviewsCache];
        renderReviewsList();
        showFormAlert(reviewAlertBox, "success", escapeHtml(i18n.t("reviews.thanks")));
      } else {
        showFormAlert(
          reviewAlertBox,
          "success",
          escapeHtml(i18n.t("reviews.pending", { phone: restaurantInfo.phone }))
        );
      }
    } catch (err) {
      showFormAlert(reviewAlertBox, "error", escapeHtml(i18n.t("errors.NETWORK")));
    } finally {
      reviewSubmitBtn.disabled = false;
      reviewSubmitBtn.classList.remove("btn-loading");
      reviewSubmitBtn.textContent = i18n.t("reviews.submit");
    }
  });

  /* Aparición escalonada al hacer scroll.
     Se marca desde JS (no desde el HTML) a propósito: si el script falla o
     el navegador no tiene IntersectionObserver, los campos nunca se ocultan. */
  function setupScrollReveal() {
    if (!("IntersectionObserver" in window)) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    // El bloque de menú de grupo se deja fuera a propósito: aparece y
    // desaparece según el número de personas y no debe depender del observer.
    const targets = Array.from(
      document.querySelectorAll(
        "#reservation-form > .section-title," +
          "#reservation-form > .form-grid > .field," +
          "#reservation-form > #submit-btn"
      )
    );
    if (!targets.length) return;

    targets.forEach((el) => el.classList.add("reveal"));

    // Los que ya entran juntos en pantalla se encadenan con un retardo
    // pequeño, para que se lean uno detrás de otro y no todos de golpe.
    let queued = 0;
    let lastShown = 0;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const now = performance.now();
          if (now - lastShown > 400) queued = 0;
          const delay = queued * 110;
          queued += 1;
          lastShown = now;
          setTimeout(() => entry.target.classList.add("is-visible"), delay);
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.15 }
    );

    targets.forEach((el) => observer.observe(el));
  }

  setupScrollReveal();

  newReservationBtn.addEventListener("click", () => {
    form.reset();
    dateInput.value = `${yyyy}-${mm}-${dd}`;
    form.style.display = "block";
    confirmation.style.display = "none";
    clearAlert();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
})();

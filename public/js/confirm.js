(function () {
  const loadingEl = document.getElementById("confirm-loading");
  const errorEl = document.getElementById("confirm-error");
  const errorText = document.getElementById("confirm-error-text");
  const questionEl = document.getElementById("confirm-question");
  const detailsEl = document.getElementById("confirm-details");
  const resultEl = document.getElementById("confirm-result");
  const resultIcon = document.getElementById("confirm-result-icon");
  const resultTitle = document.getElementById("confirm-result-title");
  const resultText = document.getElementById("confirm-result-text");
  const callHint = document.getElementById("confirm-call-hint");
  const yesBtn = document.getElementById("confirm-yes-btn");
  const noBtn = document.getElementById("confirm-no-btn");
  const langSwitcher = document.getElementById("lang-switcher");

  const PHONE = "(518) 302-5235";

  i18n.applyStaticTranslations();

  langSwitcher.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-lang]");
    if (!btn) return;
    i18n.setLang(btn.getAttribute("data-lang"));
  });

  function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str == null ? "" : str;
    return d.innerHTML;
  }

  function showOnly(el) {
    [loadingEl, errorEl, questionEl, resultEl].forEach((section) => {
      section.hidden = section !== el;
    });
  }

  const params = new URLSearchParams(window.location.search);
  const reservationId = params.get("id");

  let reservation = null;
  let currentView = "loading"; // loading | notfound | question | already-cancelled | already-confirmed | confirmed | declined | send-error

  function render() {
    if (currentView === "loading") {
      showOnly(loadingEl);
      return;
    }
    if (currentView === "notfound") {
      errorText.textContent = i18n.t("confirmPage.notFoundText", { phone: PHONE });
      showOnly(errorEl);
      return;
    }
    if (currentView === "question" && reservation) {
      detailsEl.innerHTML = `
        <dt>${i18n.t("common.name")}</dt><dd>${escapeHtml(reservation.name)}</dd>
        <dt>${i18n.t("common.date")}</dt><dd>${escapeHtml(i18n.formatDateLong(reservation.date))}</dd>
        <dt>${i18n.t("common.time")}</dt><dd>${escapeHtml(i18n.formatTime(reservation.time))}</dd>
        <dt>${i18n.t("common.partySize")}</dt><dd>${escapeHtml(String(reservation.partySize))}</dd>
      `;
      callHint.textContent = i18n.t("confirmPage.callHint", { phone: PHONE });
      showOnly(questionEl);
      return;
    }
    if (currentView === "already-cancelled") {
      resultIcon.textContent = "ℹ️";
      resultIcon.style.background = "var(--surface-alt)";
      resultIcon.style.color = "var(--text-muted)";
      resultTitle.textContent = i18n.t("confirmPage.alreadyCancelledTitle");
      resultText.textContent = i18n.t("confirmPage.alreadyCancelledText", { phone: PHONE });
      showOnly(resultEl);
      return;
    }
    if (currentView === "already-confirmed" && reservation) {
      resultIcon.textContent = "✓";
      resultIcon.style.background = "color-mix(in srgb, var(--accent) 18%, var(--surface))";
      resultIcon.style.color = "var(--accent)";
      resultTitle.textContent = i18n.t("confirmPage.alreadyConfirmedTitle");
      resultText.textContent = i18n.t("confirmPage.seeYou", {
        date: i18n.formatDateLong(reservation.date),
        time: i18n.formatTime(reservation.time),
      });
      showOnly(resultEl);
      return;
    }
    if (currentView === "confirmed" && reservation) {
      resultIcon.textContent = "✓";
      resultIcon.style.background = "color-mix(in srgb, var(--accent) 18%, var(--surface))";
      resultIcon.style.color = "var(--accent)";
      resultTitle.textContent = i18n.t("confirmPage.confirmedTitle");
      resultText.textContent = i18n.t("confirmPage.confirmedText", {
        date: i18n.formatDateLong(reservation.date),
        time: i18n.formatTime(reservation.time),
      });
      showOnly(resultEl);
      return;
    }
    if (currentView === "declined") {
      resultIcon.textContent = "✕";
      resultIcon.style.background = "color-mix(in srgb, var(--danger) 18%, var(--surface))";
      resultIcon.style.color = "var(--danger)";
      resultTitle.textContent = i18n.t("confirmPage.declinedTitle");
      resultText.textContent = i18n.t("confirmPage.declinedText");
      showOnly(resultEl);
      return;
    }
    if (currentView === "send-error") {
      resultIcon.textContent = "✕";
      resultIcon.style.background = "color-mix(in srgb, var(--danger) 18%, var(--surface))";
      resultIcon.style.color = "var(--danger)";
      resultTitle.textContent = i18n.t("confirmPage.sendErrorTitle");
      resultText.textContent = i18n.t("confirmPage.sendErrorText", { phone: PHONE });
      showOnly(resultEl);
      return;
    }
  }

  document.addEventListener("languagechange", render);

  async function loadReservation() {
    if (!reservationId) {
      currentView = "notfound";
      render();
      return;
    }
    try {
      const res = await fetch(`/api/reservations/${reservationId}`, { cache: "no-store" });
      if (!res.ok) {
        currentView = "notfound";
        render();
        return;
      }
      reservation = await res.json();

      if (reservation.status === "cancelled") {
        currentView = "already-cancelled";
      } else if (reservation.attendanceConfirmed === true) {
        currentView = "already-confirmed";
      } else {
        currentView = "question";
      }
      render();
    } catch (err) {
      currentView = "notfound";
      render();
    }
  }

  async function sendResponse(confirmed) {
    yesBtn.disabled = true;
    noBtn.disabled = true;
    try {
      const res = await fetch(`/api/reservations/${reservationId}/confirm-attendance`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmed }),
      });
      if (!res.ok) throw new Error("failed");
      currentView = confirmed ? "confirmed" : "declined";
      render();
    } catch (err) {
      currentView = "send-error";
      render();
    } finally {
      yesBtn.disabled = false;
      noBtn.disabled = false;
    }
  }

  yesBtn.addEventListener("click", () => sendResponse(true));
  noBtn.addEventListener("click", () => sendResponse(false));

  loadReservation();
})();

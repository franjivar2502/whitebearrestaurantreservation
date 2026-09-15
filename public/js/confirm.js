(function () {
  const loadingEl = document.getElementById("confirm-loading");
  const errorEl = document.getElementById("confirm-error");
  const questionEl = document.getElementById("confirm-question");
  const detailsEl = document.getElementById("confirm-details");
  const resultEl = document.getElementById("confirm-result");
  const resultIcon = document.getElementById("confirm-result-icon");
  const resultTitle = document.getElementById("confirm-result-title");
  const resultText = document.getElementById("confirm-result-text");
  const yesBtn = document.getElementById("confirm-yes-btn");
  const noBtn = document.getElementById("confirm-no-btn");

  function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str == null ? "" : str;
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

  function showOnly(el) {
    [loadingEl, errorEl, questionEl, resultEl].forEach((section) => {
      section.hidden = section !== el;
    });
  }

  const params = new URLSearchParams(window.location.search);
  const reservationId = params.get("id");

  let reservation = null;

  async function loadReservation() {
    if (!reservationId) {
      showOnly(errorEl);
      return;
    }
    try {
      const res = await fetch(`/api/reservations/${reservationId}`, { cache: "no-store" });
      if (!res.ok) {
        showOnly(errorEl);
        return;
      }
      reservation = await res.json();

      if (reservation.status === "cancelled") {
        resultIcon.textContent = "ℹ️";
        resultIcon.style.background = "var(--surface-alt)";
        resultIcon.style.color = "var(--text-muted)";
        resultTitle.textContent = "Esta reservación ya está cancelada";
        resultText.textContent = `Si fue un error, llama al restaurante al (518) 302-5235.`;
        showOnly(resultEl);
        return;
      }

      if (reservation.attendanceConfirmed === true) {
        resultIcon.textContent = "✓";
        resultTitle.textContent = "¡Ya habías confirmado tu asistencia!";
        resultText.textContent = `Te esperamos el ${formatDate(reservation.date)} a las ${formatTime(reservation.time)}`;
        showOnly(resultEl);
        return;
      }

      detailsEl.innerHTML = `
        <dt>Nombre</dt><dd>${escapeHtml(reservation.name)}</dd>
        <dt>Fecha</dt><dd>${escapeHtml(formatDate(reservation.date))}</dd>
        <dt>Hora</dt><dd>${escapeHtml(formatTime(reservation.time))}</dd>
        <dt>Personas</dt><dd>${escapeHtml(String(reservation.partySize))}</dd>
      `;
      showOnly(questionEl);
    } catch (err) {
      showOnly(errorEl);
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

      if (confirmed) {
        resultIcon.textContent = "✓";
        resultIcon.style.background = "color-mix(in srgb, var(--accent) 18%, var(--surface))";
        resultIcon.style.color = "var(--accent)";
        resultTitle.textContent = "¡Asistencia confirmada!";
        resultText.textContent = `Te esperamos el ${formatDate(reservation.date)} a las ${formatTime(reservation.time)}, gracias por confirmar.`;
      } else {
        resultIcon.textContent = "✕";
        resultIcon.style.background = "color-mix(in srgb, var(--danger) 18%, var(--surface))";
        resultIcon.style.color = "var(--danger)";
        resultTitle.textContent = "Reservación cancelada";
        resultText.textContent = "Gracias por avisarnos. Esperamos verte en otra ocasión.";
      }
      showOnly(resultEl);
    } catch (err) {
      resultIcon.textContent = "✕";
      resultTitle.textContent = "No se pudo enviar tu respuesta";
      resultText.textContent = `Intenta de nuevo, o llama al restaurante al (518) 302-5235.`;
      showOnly(resultEl);
    } finally {
      yesBtn.disabled = false;
      noBtn.disabled = false;
    }
  }

  yesBtn.addEventListener("click", () => sendResponse(true));
  noBtn.addEventListener("click", () => sendResponse(false));

  loadReservation();
})();

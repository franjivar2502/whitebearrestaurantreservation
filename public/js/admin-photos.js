(function () {
  const STORAGE_KEY = "wb-admin-password";

  const loginView = document.getElementById("login-view");
  const panelView = document.getElementById("panel-view");
  const loginAlert = document.getElementById("login-alert");
  const passwordInput = document.getElementById("password-input");
  const loginBtn = document.getElementById("login-btn");

  const addForm = document.getElementById("add-form");
  const addAlert = document.getElementById("add-alert");
  const addBtn = document.getElementById("add-btn");
  const urlInput = document.getElementById("photo-url");
  const captionInput = document.getElementById("photo-caption");
  const photoList = document.getElementById("photo-list");
  const emptyPhotos = document.getElementById("empty-photos");

  let photos = [];

  function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str == null ? "" : str;
    return d.innerHTML;
  }

  function getPassword() {
    try {
      return sessionStorage.getItem(STORAGE_KEY) || "";
    } catch (err) {
      return "";
    }
  }

  function setPassword(pw) {
    try {
      sessionStorage.setItem(STORAGE_KEY, pw);
    } catch (err) {
      /* ignorar */
    }
  }

  function showAlert(el, message) {
    el.innerHTML = `<div class="alert alert-error">${escapeHtml(message)}</div>`;
  }

  function clearAlert(el) {
    el.innerHTML = "";
  }

  async function adminFetch(path, options) {
    const opts = options || {};
    opts.headers = Object.assign({}, opts.headers, { "X-Admin-Password": getPassword() });
    return fetch(path, opts);
  }

  async function tryLogin(password) {
    const res = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    return res.ok;
  }

  function showPanel() {
    loginView.hidden = true;
    panelView.hidden = false;
    loadPhotos();
  }

  loginBtn.addEventListener("click", async () => {
    clearAlert(loginAlert);
    const password = passwordInput.value;
    if (!password) return;
    loginBtn.disabled = true;
    try {
      const ok = await tryLogin(password);
      if (ok) {
        setPassword(password);
        showPanel();
      } else {
        showAlert(loginAlert, "Contraseña incorrecta.");
      }
    } catch (err) {
      showAlert(loginAlert, "No se pudo conectar con el servidor.");
    } finally {
      loginBtn.disabled = false;
    }
  });

  passwordInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") loginBtn.click();
  });

  function renderPhotos() {
    if (!photos.length) {
      photoList.innerHTML = "";
      emptyPhotos.hidden = false;
      return;
    }
    emptyPhotos.hidden = true;
    photoList.innerHTML = photos
      .map(
        (p, i) => `
        <div class="photo-row" data-id="${escapeHtml(p.id)}">
          <img class="photo-thumb" src="${escapeHtml(p.url)}" alt="" />
          <div class="photo-info">
            <div class="photo-caption">${escapeHtml(p.caption) || "(sin descripción)"}</div>
            <div class="photo-url">${escapeHtml(p.url)}</div>
          </div>
          <div class="photo-actions">
            <button type="button" class="icon-btn" data-action="up" ${i === 0 ? "disabled" : ""} title="Subir">↑</button>
            <button type="button" class="icon-btn" data-action="down" ${i === photos.length - 1 ? "disabled" : ""} title="Bajar">↓</button>
            <button type="button" class="icon-btn danger" data-action="delete" title="Eliminar">✕</button>
          </div>
        </div>`
      )
      .join("");

    photoList.querySelectorAll(".photo-row").forEach((row) => {
      const id = row.getAttribute("data-id");
      row.querySelectorAll("[data-action]").forEach((btn) => {
        btn.addEventListener("click", () => handleAction(id, btn.getAttribute("data-action")));
      });
    });
  }

  async function loadPhotos() {
    const res = await fetch("/api/photos", { cache: "no-store" });
    photos = await res.json();
    renderPhotos();
  }

  async function saveOrder() {
    await adminFetch("/api/admin/photos/reorder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order: photos.map((p) => p.id) }),
    });
  }

  async function handleAction(id, action) {
    const index = photos.findIndex((p) => p.id === id);
    if (index === -1) return;

    if (action === "up" && index > 0) {
      [photos[index - 1], photos[index]] = [photos[index], photos[index - 1]];
      renderPhotos();
      await saveOrder();
      return;
    }
    if (action === "down" && index < photos.length - 1) {
      [photos[index + 1], photos[index]] = [photos[index], photos[index + 1]];
      renderPhotos();
      await saveOrder();
      return;
    }
    if (action === "delete") {
      if (!confirm("¿Eliminar esta foto?")) return;
      await adminFetch(`/api/admin/photos/${id}`, { method: "DELETE" });
      await loadPhotos();
    }
  }

  addForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlert(addAlert);
    addBtn.disabled = true;
    try {
      const res = await adminFetch("/api/admin/photos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: urlInput.value.trim(), caption: captionInput.value.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        showAlert(addAlert, (data.errors && data.errors[0]) || "Ocurrió un error.");
        return;
      }
      addForm.reset();
      await loadPhotos();
    } catch (err) {
      showAlert(addAlert, "No se pudo conectar con el servidor.");
    } finally {
      addBtn.disabled = false;
    }
  });

  // Si ya hay una contraseña guardada en esta pestaña, entra directo.
  const saved = getPassword();
  if (saved) {
    tryLogin(saved).then((ok) => {
      if (ok) showPanel();
    });
  }
})();

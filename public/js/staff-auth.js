/*
 * Acceso al panel de staff. Las reservaciones llevan nombre y teléfono de
 * los clientes, así que la API privada pide la contraseña de staff en la
 * cabecera X-Staff-Password. Este archivo se carga antes que tablet.js:
 * agrega esa cabecera a toda llamada a /api/ y, si el servidor responde
 * 401 (sin contraseña o ya no válida), muestra la pantalla de acceso.
 *
 * La contraseña se guarda en localStorage y no en sessionStorage a
 * propósito: la tablet del restaurante se queda encendida días enteros y
 * no tiene sentido pedirla cada vez que el navegador se cierra.
 */
(function () {
  const STORAGE_KEY = "wb-staff-password";

  function getPassword() {
    try {
      return localStorage.getItem(STORAGE_KEY) || "";
    } catch (err) {
      return "";
    }
  }

  function setPassword(pw) {
    try {
      if (pw) localStorage.setItem(STORAGE_KEY, pw);
      else localStorage.removeItem(STORAGE_KEY);
    } catch (err) {
      /* localStorage no disponible: habrá que entrar en cada carga */
    }
  }

  const view = document.getElementById("staff-login");
  const form = document.getElementById("staff-login-form");
  const input = document.getElementById("staff-login-password");
  const alertEl = document.getElementById("staff-login-alert");

  function showLogin() {
    if (!view.hidden) return;
    view.hidden = false;
    document.body.classList.add("staff-locked");
    input.value = "";
    input.focus();
  }

  function isApiCall(resource) {
    const url = typeof resource === "string" ? resource : resource && resource.url;
    if (!url) return false;
    try {
      const u = new URL(url, location.href);
      return u.origin === location.origin && u.pathname.startsWith("/api/");
    } catch (err) {
      return false;
    }
  }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = async function (resource, opts) {
    if (!isApiCall(resource)) return nativeFetch(resource, opts);
    opts = Object.assign({}, opts);
    opts.headers = Object.assign({}, opts.headers, { "X-Staff-Password": getPassword() });
    const res = await nativeFetch(resource, opts);
    if (res.status === 401) {
      setPassword("");
      showLogin();
    }
    return res;
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const password = input.value;
    if (!password) return;
    alertEl.hidden = true;
    try {
      const res = await nativeFetch("/api/staff/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) {
        alertEl.textContent = tabletI18n.t(res.status === 429 ? "login.tooMany" : "login.wrong");
        alertEl.hidden = false;
        input.select();
        return;
      }
      setPassword(password);
      // Recargar es lo más simple: el panel arranca de cero ya con acceso.
      location.reload();
    } catch (err) {
      alertEl.textContent = tabletI18n.t("login.failed");
      alertEl.hidden = false;
    }
  });

  if (!getPassword()) showLogin();
})();

/*
 * Página de políticas: muestra solo el texto del idioma activo.
 *
 * Los enlaces desde el resto del sitio usan el ancla en inglés
 * (legal.html#privacy). En inglés los id no llevan sufijo; en español y
 * francés llevan -es / -fr, así que aquí se traduce el ancla al idioma
 * activo para que el enlace caiga en la sección correcta.
 */
(function () {
  const docs = document.querySelectorAll("[data-lang-doc]");
  const langSwitcher = document.getElementById("lang-switcher");

  function sectionFor(key, lang) {
    if (!key) return null;
    const base = key.replace(/-(es|fr)$/, "");
    return document.getElementById(lang === "en" ? base : `${base}-${lang}`);
  }

  function show(lang, scrollTarget) {
    docs.forEach((doc) => {
      doc.hidden = doc.getAttribute("data-lang-doc") !== lang;
    });
    const target = sectionFor(scrollTarget, lang);
    if (target) target.scrollIntoView();
  }

  i18n.applyStaticTranslations();
  show(i18n.currentLang, decodeURIComponent(location.hash.slice(1)));

  langSwitcher.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-lang]");
    if (!btn) return;
    i18n.setLang(btn.getAttribute("data-lang"));
    show(i18n.currentLang, null);
    window.scrollTo(0, 0);
  });
})();

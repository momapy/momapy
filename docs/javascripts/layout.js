// The layout toggle is hidden (see docs/stylesheets/extra.css): keep the
// initial fixed layout, dropping a full layout a visitor chose before.
localStorage.removeItem("html-layout");
document.documentElement.classList.replace("layout-full", "layout-fixed");

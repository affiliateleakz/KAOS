
(function () {
  function isHome() {
    return (location.pathname.replace(/\/+$/, "") || "/") === "/";
  }
  if (!isHome()) return;

  function mount() {
    var root = document.getElementById("root");
    if (!root) return setTimeout(mount, 25);

    document.documentElement.classList.add("kaos-exact-home-active");
    document.body.classList.add("kaos-exact-home-active");

    root.innerHTML = `
      <main class="kx-home" aria-label="KAOS Trading Bot">
        <div class="kx-stage">
          <img class="kx-reference" src="/kaos-home-target.png?v=210" alt="KAOS Trading Bot — Trade With KAOS">

          <nav class="kx-hotspots" aria-label="Homepage navigation">
            <a class="kx-hit kx-home-link" href="/" aria-label="Home"></a>
            <a class="kx-hit kx-bot-link" href="#systems" aria-label="KAOS Bot"></a>
            <a class="kx-hit kx-features-link" href="#systems" aria-label="Features"></a>
            <a class="kx-hit kx-pricing-link" href="/register" aria-label="Pricing"></a>
            <a class="kx-hit kx-results-link" href="#systems" aria-label="Results"></a>
            <a class="kx-hit kx-faq-link" href="#systems" aria-label="FAQ"></a>
            <a class="kx-hit kx-login-link" href="/login" aria-label="Login"></a>
            <a class="kx-hit kx-get-link" href="/register" aria-label="Get KAOS"></a>
            <a class="kx-hit kx-getbot-link" href="/register" aria-label="Get KAOS Trading Bot"></a>
            <a class="kx-hit kx-demo-link" href="#systems" aria-label="Watch Demo"></a>
            <a class="kx-hit kx-start-link" href="/register" aria-label="Start Trading With KAOS"></a>
          </nav>

          <div id="systems" class="kx-system-anchor" aria-hidden="true"></div>
        </div>
      </main>`;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount, {once:true});
  } else {
    mount();
  }
})();

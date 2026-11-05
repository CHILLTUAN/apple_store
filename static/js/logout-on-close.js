const logoutScript = document.currentScript;
const logoutUrl = logoutScript?.dataset.logoutUrl;
const csrfToken = logoutScript?.dataset.csrfToken;
let navigatingWithinSite = false;

document.addEventListener(
  "click",
  (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }

    const link = event.target.closest("a[href]");
    if (!link || link.hasAttribute("download")) {
      return;
    }

    const target = link.getAttribute("target");
    const destination = new URL(link.href, window.location.href);
    if (
      (!target || target === "_self")
      && destination.origin === window.location.origin
      && (
        destination.pathname !== window.location.pathname
        || destination.search !== window.location.search
      )
    ) {
      navigatingWithinSite = true;
    }
  },
  true,
);

document.addEventListener(
  "submit",
  (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
      return;
    }

    const target = form.getAttribute("target");
    const destination = new URL(form.action, window.location.href);
    if (
      (!target || target === "_self")
      && destination.origin === window.location.origin
    ) {
      navigatingWithinSite = true;
    }
  },
  true,
);

window.addEventListener("pagehide", (event) => {
  if (event.persisted || navigatingWithinSite || !logoutUrl || !csrfToken) {
    return;
  }

  const body = new URLSearchParams({ csrf_token: csrfToken });
  if (!navigator.sendBeacon(logoutUrl, body)) {
    fetch(logoutUrl, {
      method: "POST",
      body,
      credentials: "same-origin",
      keepalive: true,
    });
  }
});

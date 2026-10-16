(function () {
  "use strict";

  const SCHEDULE = globalThis.CEASLOVNIC_SCHEDULE;
  const TZ = globalThis.CEASLOVNIC_TZ;
  const frame = document.getElementById("player-frame");
  const nowEl = document.getElementById("status-now");
  const slotEl = document.getElementById("status-slot");
  const nextEl = document.getElementById("status-next");

  // Returns {h, m, hhmm, label} for the current moment in Europe/Chisinau.
  function nowInZone() {
    const parts = new Intl.DateTimeFormat("en-GB", {
      timeZone: TZ,
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      weekday: "short",
      day: "2-digit",
      month: "short"
    }).formatToParts(new Date());
    const get = (t) => parts.find((p) => p.type === t)?.value || "";
    const h = Number.parseInt(get("hour"), 10);
    const m = Number.parseInt(get("minute"), 10);
    const s = Number.parseInt(get("second"), 10);
    const hhmm = String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0");
    const label =
      get("weekday") + " " + get("day") + " " + get("month") + " · " +
      hhmm + ":" + String(s).padStart(2, "0");
    return { h, m, s, hhmm, label, minutes: h * 60 + m };
  }

  function toMinutes(hhmm) {
    const [h, m] = hhmm.split(":").map(Number);
    return h * 60 + m;
  }

  // Find the slot that should be on screen right now.
  // Rule: most recent slot whose start time is <= now. If now < first slot, wrap to the last slot of the previous day.
  function activeSlot(nowMin) {
    let chosen = null;
    for (const slot of SCHEDULE) {
      if (toMinutes(slot.time) <= nowMin) chosen = slot;
      else break;
    }
    return chosen || SCHEDULE[SCHEDULE.length - 1]; // before first slot ⇒ previous day's last
  }

  function nextSlot(nowMin) {
    for (const slot of SCHEDULE) {
      if (toMinutes(slot.time) > nowMin) return slot;
    }
    return SCHEDULE[0]; // wraps to tomorrow
  }

  // ── Service worker & PWA ────────────────────────────────────────────────
  // Registering the SW enables (a) offline caching for the whole site and
  // (b) Notification Triggers — scheduled reminders that fire even when
  // the player tab is closed, on browsers that support TimestampTrigger
  // (currently Chromium-based desktop & Android). Falls back to the in-tab
  // tick-based notifications otherwise.
  let triggersAvailable = false;
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js")
      .then(() => {
        triggersAvailable = globalThis.TimestampTrigger !== undefined;
      })
      .catch((err) => console.warn("Pravoslavnic: SW registration failed", err));
  }

  // ── Notifications ────────────────────────────────────────────────────────
  // A 5-minute reminder fires before each slot, once per upcoming slot.
  // Opt-in via the 🔔 button; state persists in localStorage.
  const REMINDER_OFFSET = 5;
  const NOTIF_KEY = "pravoslavnic.notify";
  const notifBtn = document.getElementById("notif-btn");
  let lastNotifiedSlug = null;

  const notifSupported = "Notification" in globalThis;

  function notifEnabled() {
    return (
      notifSupported &&
      Notification.permission === "granted" &&
      localStorage.getItem(NOTIF_KEY) === "1"
    );
  }

  function updateNotifBtn() {
    if (!notifSupported) {
      notifBtn.style.display = "none";
      return;
    }
    const on = notifEnabled();
    notifBtn.textContent = on ? "🔔" : "🔕";
    notifBtn.title = on
      ? "Notificările sunt active. Atinge pentru a opri."
      : "Activează notificările pentru fiecare ceas (cu 5 min înainte).";
    notifBtn.setAttribute("aria-pressed", on ? "true" : "false");
  }

  function minutesUntil(nowMin, slot) {
    let diff = toMinutes(slot.time) - nowMin;
    if (diff < 0) diff += 24 * 60;
    return diff;
  }

  // Schedule one TimestampTrigger per upcoming slot via the service-worker
  // registration. Fires even when the tab is closed on browsers that support
  // the Notification Triggers API (Chromium-based). No-op otherwise.
  async function scheduleSWReminders() {
    if (!triggersAvailable || !notifEnabled()) return;
    let reg;
    try { reg = await navigator.serviceWorker.ready; } catch { return; }
    const t = nowInZone();
    for (const slot of SCHEDULE) {
      const ahead = minutesUntil(t.minutes, slot);
      if (ahead <= REMINDER_OFFSET) continue;       // too late to remind
      const ts = Date.now() + (ahead - REMINDER_OFFSET) * 60_000;
      try {
        await reg.showNotification("Pravoslavnic", {
          body: `În ${REMINDER_OFFSET} min: ${slot.title} (${slot.time})`,
          icon: "css/chi-rho.png",
          tag: "pravoslavnic-" + slot.slug,           // same tag replaces on reschedule
          showTrigger: new globalThis.TimestampTrigger(ts),
        });
      } catch (err) {
        console.warn("Pravoslavnic: schedule failed for " + slot.slug, err);
      }
    }
  }

  async function clearSWReminders() {
    if (!("serviceWorker" in navigator)) return;
    try {
      const reg = await navigator.serviceWorker.ready;
      const all = await reg.getNotifications({ includeTriggered: false });
      for (const n of all) {
        if (n.tag?.startsWith("pravoslavnic-")) n.close();
      }
    } catch (err) {
      console.warn("Pravoslavnic: clear failed", err);
    }
  }

  async function toggleNotif() {
    if (!notifSupported) return;
    if (Notification.permission === "denied") {
      alert("Notificările sunt blocate de browser. Activează-le din setările site-ului.");
      return;
    }
    if (Notification.permission === "default") {
      const result = await Notification.requestPermission();
      if (result !== "granted") {
        updateNotifBtn();
        return;
      }
    }
    if (localStorage.getItem(NOTIF_KEY) === "1") {
      localStorage.removeItem(NOTIF_KEY);
      await clearSWReminders();
    } else {
      localStorage.setItem(NOTIF_KEY, "1");
      await scheduleSWReminders();
    }
    updateNotifBtn();
  }

  notifBtn.addEventListener("click", toggleNotif);
  updateNotifBtn();
  // If notifications were already enabled from a previous session, refresh
  // the SW-scheduled reminders for the next 24h on this load.
  if (notifEnabled()) scheduleSWReminders();

  function fireReminder(slot, minutes) {
    // The SW path (Notification Triggers) covers tab-closed delivery on
    // supporting browsers. When that's active, skip the in-tab fallback so
    // we don't double up.
    if (!notifEnabled() || triggersAvailable) return;
    try {
      new Notification("Pravoslavnic", {
        body: `În ${minutes} min: ${slot.title} (${slot.time})`,
        icon: "css/chi-rho.png",
        tag: "pravoslavnic-reminder",
      });
    } catch (err) {
      // Some browsers (e.g. mobile Safari) require the ServiceWorker path —
      // log so the user can debug from devtools, but don't break the loop.
      console.warn("Pravoslavnic: notification failed", err);
    }
  }

  // ── Main tick ────────────────────────────────────────────────────────────
  let currentSlug = null;

  function tick() {
    const t = nowInZone();
    const active = activeSlot(t.minutes);
    const next = nextSlot(t.minutes);

    nowEl.textContent = t.label;
    slotEl.textContent = active.time + " · " + active.title;
    nextEl.textContent = "Următor: " + next.time + " · " + next.title;

    // Fire the reminder once when the upcoming slot is within the offset window.
    const untilNext = minutesUntil(t.minutes, next);
    if (untilNext > 0 && untilNext <= REMINDER_OFFSET && next.slug !== lastNotifiedSlug) {
      fireReminder(next, untilNext);
      lastNotifiedSlug = next.slug;
    }

    if (active.slug !== currentSlug) {
      // We've just rolled into the slot we previously notified about; clear
      // the marker so the *next* upcoming slot can be notified about.
      if (active.slug === lastNotifiedSlug) lastNotifiedSlug = null;
      // Each slot transition refreshes the rolling 24h schedule of triggers,
      // so the slot we just consumed gets replaced with one for ~24h later.
      if (currentSlug !== null) scheduleSWReminders();
      currentSlug = active.slug;
      frame.src = "content/" + active.slug + ".html";
      document.title = "Pravoslavnic · " + active.title;
    }
  }

  // Fullscreen toggle on click of the small badge.
  const fsBtn = document.getElementById("fs-btn");
  fsBtn.addEventListener("click", () => {
    if (document.fullscreenElement) {
      document.exitFullscreen?.();
    } else {
      document.documentElement.requestFullscreen?.();
    }
  });

  // ── PWA install nudge ─────────────────────────────────────────────────────
  // Chromium-based browsers fire `beforeinstallprompt` once the PWA criteria
  // are met. We stash the event, reveal the install button, and call prompt()
  // on click. Hidden again once accepted or after `appinstalled`. iOS Safari
  // never fires this event (Add to Home Screen is manual via Share); the
  // button just stays hidden there.
  const installBtn = document.getElementById("install-btn");
  let deferredInstallPrompt = null;
  globalThis.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredInstallPrompt = e;
    installBtn.hidden = false;
  });
  installBtn.addEventListener("click", async () => {
    if (!deferredInstallPrompt) return;
    deferredInstallPrompt.prompt();
    try {
      await deferredInstallPrompt.userChoice;
    } catch (err) {
      console.warn("Pravoslavnic: install prompt failed", err);
    }
    deferredInstallPrompt = null;
    installBtn.hidden = true;
  });
  globalThis.addEventListener("appinstalled", () => {
    installBtn.hidden = true;
    deferredInstallPrompt = null;
  });

  // First render, then align to the next wall-clock second so the seconds in the status bar tick cleanly.
  tick();
  const msToNextSecond = 1000 - (new Date().getMilliseconds());
  setTimeout(function alignedLoop() {
    tick();
    setInterval(tick, 1000);
  }, msToNextSecond);
})();

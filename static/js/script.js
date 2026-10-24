/* ==========================================================================
   GGZONE — client-side behaviour
   ========================================================================== */
document.addEventListener("DOMContentLoaded", () => {
  initNavToggle();
  initGameSearch();
  initBookingForm();
  initFormValidation();
  initAlerts();
});

/* ---------- Mobile navigation ---------- */
function initNavToggle() {
  const toggle = document.getElementById("navToggle");
  const nav = document.getElementById("mainNav");
  if (!toggle || !nav) return;

  toggle.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
  });
}

/* ---------- Live game search ---------- */
function initGameSearch() {
  const input = document.getElementById("gameSearch");
  if (!input) return;

  const cards = document.querySelectorAll(".searchable-game");

  input.addEventListener("input", () => {
    const query = input.value.trim().toLowerCase();
    cards.forEach((card) => {
      const haystack = (card.dataset.search || "").toLowerCase();
      card.style.display = haystack.includes(query) ? "" : "none";
    });
  });
}

/* ---------- Booking form: no past dates, end after start ---------- */
function initBookingForm() {
  const form = document.getElementById("bookingForm");
  if (!form) return;

  const dateInput = document.getElementById("bookingDate");
  if (dateInput) {
    const now = new Date();
    const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
    dateInput.min = local.toISOString().split("T")[0];
  }

  form.addEventListener("submit", (event) => {
    const start = form.elements["start_time"].value;
    const end = form.elements["end_time"].value;

    if (start && end && end <= start) {
      event.preventDefault();
      alert("End time must be later than start time.");
    }
  });
}

/* ---------- Basic validation styling ---------- */
function initFormValidation() {
  document.querySelectorAll("form[data-validate]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      let valid = true;
      form.querySelectorAll("input[required]").forEach((field) => {
        const ok = field.checkValidity();
        field.classList.toggle("invalid", !ok);
        if (!ok) valid = false;
      });
      if (!valid) event.preventDefault();
    });
  });
}

/* ---------- Auto-dismiss flash messages ---------- */
function initAlerts() {
  document.querySelectorAll(".alert").forEach((alertBox) => {
    setTimeout(() => {
      alertBox.style.opacity = "0";
      setTimeout(() => alertBox.remove(), 400);
    }, 5000);
  });
}

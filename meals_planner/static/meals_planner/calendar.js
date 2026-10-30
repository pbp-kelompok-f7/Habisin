(() => {
  "use strict";
  const root = document.querySelector(".planner");
  const panel = document.querySelector(".planner-calendar");
  if (!root || !panel) return;

  let calendar = JSON.parse(document.getElementById("planner-calendar-state").textContent);
  let weekState = JSON.parse(document.getElementById("planner-state").textContent);
  let selectedDate = root.dataset.selectedDate;
  let revision = 0;
  let requestId = 0;
  let controller = null;
  let loading = false;
  const grid = document.getElementById("calendar-grid");
  const status = document.getElementById("calendar-status");
  const controls = [...panel.querySelectorAll("button")];

  function dateForDay(week, day) {
    const date = new Date(`${week}T12:00:00Z`);
    date.setUTCDate(date.getUTCDate() + day);
    return date.toISOString().slice(0, 10);
  }

  function saving() {
    return root.getAttribute("aria-busy") === "true";
  }

  function syncControls() {
    controls.forEach(button => {
      button.disabled = loading || saving() ||
        (button.hasAttribute("data-calendar-direction") && !button.dataset.calendarMonth);
    });
  }

  function announce(message, error = false, loginUrl = null) {
    status.textContent = message;
    status.classList.toggle("is-error", error);
    if (loginUrl) {
      const url = new URL(loginUrl, window.location.origin);
      if (url.origin === window.location.origin) {
        url.searchParams.set("next", window.location.pathname + window.location.search);
        const link = document.createElement("a");
        link.href = url.href;
        link.textContent = "Sign in again";
        status.append(" ", link);
      }
    }
  }

  function syncCounts() {
    calendar.days.forEach(day => {
      if (day.week === weekState.week) day.count = weekState.counts[day.weekday];
    });
    const monthDays = calendar.days.filter(day => day.in_month);
    calendar.total = monthDays.reduce((sum, day) => sum + day.count, 0);
    calendar.scheduled_days = monthDays.filter(day => day.count > 0).length;
  }

  function renderCalendar() {
    document.getElementById("calendar-month-label").textContent = calendar.label;
    panel.querySelector('[data-calendar-direction="previous"]').dataset.calendarMonth = calendar.previous_month || "";
    panel.querySelector('[data-calendar-direction="next"]').dataset.calendarMonth = calendar.next_month || "";
    grid.replaceChildren(...calendar.days.map(day => {
      const cell = document.createElement(day.selectable ? "a" : "span");
      if (day.selectable) cell.href = day.url;
      else cell.setAttribute("aria-disabled", "true");
      cell.className = "calendar-day";
      cell.classList.toggle("is-outside", !day.in_month);
      cell.classList.toggle("is-today", day.is_today);
      cell.classList.toggle("is-selected", day.date === selectedDate);
      cell.dataset.calendarDate = day.date;
      cell.dataset.calendarWeek = day.week;
      cell.dataset.calendarDay = day.weekday;
      cell.dataset.count = day.count;
      cell.setAttribute("aria-label", `${day.label}, ${day.count} of 3 meals${day.is_today ? ", today" : ""}${day.date === selectedDate ? ", selected" : ""}`);
      if (day.date === selectedDate) cell.setAttribute("aria-current", "date");
      const number = document.createElement("time");
      number.className = "calendar-day-number";
      number.dateTime = day.date;
      number.textContent = day.day;
      const dots = document.createElement("span");
      dots.className = "calendar-dots";
      dots.setAttribute("aria-hidden", "true");
      for (let i = 0; i < 3; i++) {
        const dot = document.createElement("span");
        dot.className = `calendar-dot${i < day.count ? " is-filled" : ""}`;
        dots.append(dot);
      }
      cell.append(number, dots);
      return cell;
    }));
    document.getElementById("calendar-summary").textContent =
      `${calendar.total} meals across ${calendar.scheduled_days} days this month`;
    syncControls();
  }

  function selectDate(day) {
    if (saving()) {
      announce("Please wait until the meal finishes saving before selecting a date.");
      return;
    }
    if (day.week === weekState.week) {
      root.dispatchEvent(new CustomEvent("planner:selectday", {detail: {day: day.weekday}}));
      grid.querySelector(`[data-calendar-date="${day.date}"]`)?.focus();
    } else {
      window.location.assign(day.url);
    }
  }

  async function loadMonth(month, goToday = false) {
    if (saving()) return;
    const id = ++requestId;
    const startRevision = revision;
    const restoreDateFocus = grid.contains(document.activeElement);
    const initiatingControl = controls.includes(document.activeElement) ? document.activeElement : null;
    let selectedToday = false;
    controller?.abort();
    controller = new AbortController();
    loading = true;
    panel.setAttribute("aria-busy", "true");
    syncControls();
    announce("Loading calendar...");
    let loginUrl = null;
    try {
      const url = new URL(root.dataset.calendarUrl, window.location.origin);
      if (month) url.searchParams.set("month", month);
      const response = await fetch(url, {credentials: "same-origin", signal: controller.signal, cache: "no-store"});
      const data = await response.json().catch(() => null);
      if (response.status === 401 || response.redirected) {
        loginUrl = data?.login_url || response.url;
        throw new Error("Session expired. Sign in again to view the calendar.");
      }
      if (!response.ok || !Array.isArray(data?.days) || data.days.length !== 42) {
        throw new Error(data?.error || "Calendar could not be loaded. Try the month button again.");
      }
      if (id !== requestId) return;
      calendar = data;
      // A save can finish while this GET is in flight; keep its newer counts.
      if (revision !== startRevision) syncCounts();
      renderCalendar();
      announce(`Calendar ${calendar.label} displayed.`);
      if (restoreDateFocus) grid.querySelector(`[data-calendar-date="${selectedDate}"]`)?.focus();
      if (goToday) {
        const today = calendar.days.find(day => day.date === calendar.today);
        if (today?.selectable && !saving()) {
          selectDate(today);
          selectedToday = true;
        }
      }
    } catch (error) {
      if (error.name !== "AbortError" && id === requestId) {
        announce(error instanceof TypeError
          ? "Connection lost. Previous calendar remains displayed; try again."
          : error.message, true, loginUrl);
      }
    } finally {
      if (id === requestId) {
        loading = false;
        panel.removeAttribute("aria-busy");
        syncControls();
        if (!selectedToday && initiatingControl && !initiatingControl.disabled &&
            (document.activeElement === document.body || document.activeElement === initiatingControl)) {
          initiatingControl.focus();
        }
      }
    }
  }

  panel.querySelectorAll("[data-calendar-direction]").forEach(button => {
    button.addEventListener("click", () => {
      if (button.dataset.calendarMonth) loadMonth(button.dataset.calendarMonth);
    });
  });
  panel.querySelector("[data-calendar-today]").addEventListener("click", () => loadMonth(null, true));
  grid.addEventListener("click", event => {
    const link = event.target.closest("a[data-calendar-date]");
    if (!link || !grid.contains(link) || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    if (saving()) {
      event.preventDefault();
      announce("Please wait until the meal finishes saving before selecting a date.");
      return;
    }
    const day = calendar.days.find(day => day.date === link.dataset.calendarDate);
    if (day?.week === weekState.week) {
      event.preventDefault();
      selectDate(day);
    }
  });
  grid.addEventListener("keydown", event => {
    const cell = event.target.closest("a[data-calendar-date]");
    if (!cell || event.ctrlKey || event.metaKey || event.altKey) return;
    const index = calendar.days.findIndex(day => day.date === cell.dataset.calendarDate);
    const offsets = {ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7,
      Home: -(index % 7), End: 6 - (index % 7)};
    if (!(event.key in offsets)) return;
    event.preventDefault();
    const target = calendar.days[index + offsets[event.key]];
    if (target?.selectable) grid.querySelector(`[data-calendar-date="${target.date}"]`)?.focus();
  });
  root.addEventListener("planner:statechange", event => {
    const {state, selectedDay, reason} = event.detail;
    const changed = state !== weekState;
    weekState = state;
    selectedDate = dateForDay(state.week, selectedDay);
    root.dataset.selectedDate = selectedDate;
    if (changed) {
      revision++;
      syncCounts();
    }
    // A month request may have a newer clock than a page opened before midnight.
    if (state.today_date && state.today_date >= calendar.today) {
      calendar.today = state.today_date;
      calendar.days.forEach(day => { day.is_today = day.date === state.today_date; });
    }
    const restoreDateFocus = grid.contains(document.activeElement);
    renderCalendar();
    if (restoreDateFocus) grid.querySelector(`[data-calendar-date="${selectedDate}"]`)?.focus();
    if (reason === "selection" && selectedDate.slice(0, 7) !== calendar.month) {
      loadMonth(selectedDate.slice(0, 7));
    }
  });
  root.addEventListener("planner:busychange", syncControls);
  syncControls();
})();

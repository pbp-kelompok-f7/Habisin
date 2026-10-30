(() => {
  "use strict";
  const root = document.querySelector(".planner");
  if (!root) return;
  let state = JSON.parse(document.getElementById("planner-state").textContent);
  let recipeById = new Map(state.recipes.map(recipe => [recipe.id, recipe]));
  const tabs = [...document.querySelectorAll("[data-day]")];
  const cards = [...document.querySelectorAll("[data-slot]")];
  const dialog = document.getElementById("recipe-dialog");
  const search = document.getElementById("recipe-search");
  const status = document.getElementById("planner-status");
  const recipeOptions = document.querySelector(".recipe-options");
  const recipeMessage = document.getElementById("recipe-no-results");
  const recoveryLinks = [document.getElementById("planner-recovery"), document.getElementById("dialog-recovery")];
  let selectedDay = Number(root.dataset.selectedDay);
  let editingSlot = null;
  let opener = null;
  let saving = false;
  let defaultChoices = null;
  let searchController = null;
  let searchTimer = null;
  const navigation = document.querySelector(".planner-nav, .site-header nav > div:first-child");
  const activeNavigation = navigation?.querySelector('.is-active, [aria-current="page"]');
  if (activeNavigation && navigation.scrollWidth > navigation.clientWidth) {
    const navBounds = navigation.getBoundingClientRect();
    const activeBounds = activeNavigation.getBoundingClientRect();
    navigation.scrollLeft = activeBounds.left - navBounds.left - (navigation.clientWidth - activeBounds.width) / 2;
  }

  function announce(message, error = false) {
    status.textContent = message;
    status.classList.toggle("is-error", error);
  }

  function clearRecovery() {
    recoveryLinks.forEach(link => { link.hidden = true; });
  }

  function showRecovery(loginUrl) {
    let target = new URL(window.location.href);
    target.searchParams.set("week", state.week);
    target.searchParams.set("day", selectedDay);
    let label = "Muat ulang";
    if (loginUrl) {
      const login = new URL(loginUrl, window.location.origin);
      if (login.origin === window.location.origin) {
        login.searchParams.set("next", target.pathname + target.search);
        target = login;
        label = "Masuk lagi";
      }
    }
    recoveryLinks.forEach(link => {
      link.href = target.href;
      link.textContent = label;
      link.hidden = false;
    });
  }

  function render(reason = "update") {
    const meals = state.meals[String(selectedDay)] || {};
    document.getElementById("planner-subtitle").textContent = selectedDay === state.today
      ? "Menu untuk hari ini!" : `Menu untuk hari ${tabs[selectedDay].dataset.name}!`;
    tabs.forEach((tab, index) => {
      tab.classList.toggle("is-selected", index === selectedDay);
      if (index === selectedDay) tab.setAttribute("aria-current", "date");
      else tab.removeAttribute("aria-current");
      tab.querySelector(".today-label")?.remove();
      if (index === state.today) {
        const todayLabel = document.createElement("span");
        todayLabel.className = "today-label";
        todayLabel.textContent = " · hari ini";
        tab.firstElementChild.append(todayLabel);
      }
    });
    const currentWeekControl = document.querySelector(".week-current");
    const isCurrentWeek = state.week === state.current_week;
    const currentWeekLink = document.createElement(isCurrentWeek ? "span" : "a");
    currentWeekLink.className = `week-current${isCurrentWeek ? " is-current" : ""}`;
    currentWeekLink.textContent = "Minggu ini";
    if (!isCurrentWeek) {
      const url = new URL(window.location.href);
      url.searchParams.set("week", state.current_week);
      url.searchParams.delete("day");
      currentWeekLink.href = url.href;
      currentWeekLink.dataset.weekLink = "";
    }
    currentWeekControl.replaceWith(currentWeekLink);
    document.querySelectorAll(".week-arrow").forEach(link => {
      const url = new URL(link.href);
      url.searchParams.set("day", selectedDay);
      link.href = url.href;
    });
    cards.forEach(card => {
      const recipe = recipeById.get(meals[card.dataset.slot]);
      card.classList.toggle("is-empty", !recipe);
      card.querySelector(".meal-name").textContent = recipe?.name || "";
      card.querySelector(".meal-name").hidden = !recipe;
      card.querySelector(".meal-add").hidden = !!recipe;
      card.querySelector(".meal-actions").hidden = !recipe;
    });
    document.getElementById("weekly-total").textContent = state.total;
    document.querySelectorAll("[data-progress-day]").forEach(link => {
      const day = Number(link.dataset.progressDay);
      link.querySelector("span").textContent = `${state.counts[day]}/3`;
      link.classList.toggle("is-selected", day === selectedDay);
      if (day === selectedDay) link.setAttribute("aria-current", "date");
      else link.removeAttribute("aria-current");
    });
    document.getElementById("ingredient-list").replaceChildren(...state.ingredients.map(ingredient => {
      const item = document.createElement("li");
      item.textContent = ingredient;
      return item;
    }));
    const emptyIngredients = document.getElementById("shopping-empty");
    emptyIngredients.hidden = state.ingredients.length > 0;
    emptyIngredients.textContent = state.total
      ? "Daftar bahan belum tersedia untuk menu yang dipilih."
      : "Tambahkan menu untuk melihat daftar bahannya.";
    document.getElementById("ingredients-incomplete").hidden = !state.missing_ingredients;
    root.dispatchEvent(new CustomEvent("planner:statechange", {detail: {state, selectedDay, reason}}));
  }

  function recipeOption(recipe) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "recipe-option";
    button.dataset.recipe = recipe.id;
    button.disabled = saving;
    const image = document.createElement("img");
    image.src = recipe.image_url;
    image.width = 88;
    image.height = 76;
    image.alt = "";
    image.loading = "lazy";
    const copy = document.createElement("span");
    copy.className = "recipe-option-copy";
    const name = document.createElement("strong");
    name.textContent = recipe.name;
    const saved = document.createElement("span");
    saved.className = `recipe-source${recipe.saved ? "" : " is-unsaved"}`;
    saved.textContent = recipe.saved ? "Tersimpan" : "Belum disimpan";
    const ingredients = document.createElement("span");
    ingredients.className = "recipe-ingredients";
    ingredients.textContent = recipe.ingredients.length ? recipe.ingredients.join(", ") : "Bahan belum tersedia";
    copy.append(name, saved, ingredients);
    const plus = document.createElement("span");
    plus.className = "recipe-option-plus";
    plus.setAttribute("aria-hidden", "true");
    plus.textContent = "+";
    button.append(image, copy, plus);
    return button;
  }

  function showRecipes(choices, emptyMessage) {
    recipeOptions.replaceChildren(...choices.map(recipeOption));
    recipeMessage.textContent = choices.length ? "" : emptyMessage;
    recipeMessage.hidden = choices.length > 0;
  }

  async function loadRecipes() {
    const query = search.value.trim();
    if (!query && defaultChoices) {
      searchController?.abort();
      showRecipes(defaultChoices, "Belum ada resep untuk ditampilkan.");
      return;
    }
    searchController?.abort();
    searchController = new AbortController();
    recipeOptions.replaceChildren();
    recipeMessage.textContent = query ? `Mencari "${query}" di TheMealDB...` : "Memuat resep...";
    recipeMessage.hidden = false;
    try {
      const url = new URL(root.dataset.recipesUrl, window.location.origin);
      if (query) url.searchParams.set("q", query);
      const response = await fetch(url, {credentials: "same-origin", signal: searchController.signal});
      const data = await response.json().catch(() => null);
      if (response.status === 401) {
        showRecovery(data?.login_url);
        throw new Error(data?.error);
      }
      if (!response.ok || !Array.isArray(data?.recipes)) throw new Error();
      if (!query) defaultChoices = data.recipes;
      if (query === search.value.trim()) {
        showRecipes(data.recipes, query ? "Resep belum ditemukan. Coba nama resep atau bahan lain dalam bahasa Inggris." : "Belum ada resep untuk ditampilkan.");
      }
    } catch (error) {
      if (error.name === "AbortError") return;
      showRecipes([], error.message || "Resep belum dapat dimuat. Periksa koneksi lalu coba lagi.");
    }
  }

  function scheduleSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadRecipes, 350);
  }

  function selectDay(day, updateUrl = true) {
    if (saving && updateUrl) return;
    if (!Number.isInteger(day) || day < 0 || day > 6) return;
    selectedDay = day;
    if (updateUrl) {
      const url = new URL(window.location.href);
      url.searchParams.set("week", state.week);
      url.searchParams.set("day", day);
      history.pushState(null, "", url);
    }
    if (!saving) {
      announce("");
      clearRecovery();
    }
    render("selection");
  }

  root.addEventListener("planner:selectday", event => selectDay(event.detail.day));

  document.querySelectorAll("[data-day], [data-progress-day]").forEach(link => {
    link.addEventListener("click", event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      selectDay(Number(link.dataset.day ?? link.dataset.progressDay));
    });
  });
  document.querySelector(".planner-week").addEventListener("click", event => {
    if (saving && event.target.closest("[data-week-link]")) {
      event.preventDefault();
      announce("Tunggu sampai menu selesai disimpan sebelum mengganti minggu.");
    }
  });
  window.addEventListener("popstate", () => {
    const url = new URL(window.location.href);
    if ((url.searchParams.get("week") || state.current_week) !== state.week) {
      window.location.reload();
      return;
    }
    if (dialog.open && !saving) dialog.close();
    const rawDay = url.searchParams.get("day");
    selectDay(/^[0-6]$/.test(rawDay || "") ? Number(rawDay) : (state.today ?? 0), false);
  });

  document.querySelectorAll("[data-edit]").forEach(button => {
    button.addEventListener("click", () => {
      if (saving) return;
      editingSlot = button.dataset.edit;
      opener = button;
      const card = cards.find(card => card.dataset.slot === editingSlot);
      const hasRecipe = !!state.meals[String(selectedDay)]?.[editingSlot];
      document.getElementById("recipe-dialog-title").textContent = hasRecipe ? "Ganti menu" : "Tambah menu";
      document.getElementById("recipe-dialog-day").textContent = `${tabs[selectedDay].dataset.name}, ${tabs[selectedDay].dataset.dateLabel} · ${card.dataset.label}`;
      document.getElementById("dialog-error").textContent = "";
      clearRecovery();
      search.value = "";
      clearTimeout(searchTimer);
      loadRecipes();
      dialog.showModal();
      search.focus();
    });
  });
  search.addEventListener("input", scheduleSearch);
  document.getElementById("recipe-form").addEventListener("submit", event => event.preventDefault());
  dialog.querySelector(".dialog-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", event => {
    const rect = dialog.getBoundingClientRect();
    if (!saving && event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
  });
  dialog.addEventListener("cancel", event => { if (saving) event.preventDefault(); });
  dialog.addEventListener("close", () => {
    const card = cards.find(card => card.dataset.slot === editingSlot);
    const target = opener?.offsetParent ? opener : card?.querySelector(".meal-change");
    if (!saving) target?.focus();
    editingSlot = null;
  });

  async function saveMeal(slot, recipe) {
    if (saving || !slot) return;
    saving = true;
    root.setAttribute("aria-busy", "true");
    document.querySelectorAll(".planner button, .recipe-dialog button").forEach(button => { button.disabled = true; });
    root.dispatchEvent(new CustomEvent("planner:busychange"));
    document.getElementById("dialog-error").textContent = "";
    clearRecovery();
    announce("Menyimpan menu...");
    const day = selectedDay;
    let focusAfterSave = null;
    let loginUrl = null;
    try {
      const response = await fetch(root.dataset.updateUrl, {
        method: "POST",
        headers: {"X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value},
        body: new URLSearchParams({week: state.week, day: String(day), slot, recipe}),
        credentials: "same-origin",
      });
      const data = await response.json().catch(() => null);
      if (response.status === 401 || response.redirected) {
        loginUrl = data?.login_url || (response.redirected ? response.url : null);
        throw new Error("Sesi masukmu berakhir. Masuk lagi untuk menyimpan menu.");
      }
      if (!response.ok || !data?.meals || !Array.isArray(data.counts)) {
        const fallback = response.status === 403
          ? "Sesi keamanan berubah. Muat ulang halaman sebelum menyimpan menu."
          : "Menu belum dapat diperbarui. Muat ulang halaman dan coba lagi.";
        throw new Error(data?.error || fallback);
      }
      state = data;
      recipeById = new Map(state.recipes.map(recipe => [recipe.id, recipe]));
      render();
      focusAfterSave = cards.find(card => card.dataset.slot === slot)?.querySelector(recipe ? ".meal-change" : ".meal-add");
      if (dialog.open) dialog.close();
      announce(recipe ? "Menu tersimpan di akunmu. Ringkasan mingguan sudah diperbarui." : "Menu dihapus. Ringkasan mingguan sudah diperbarui.");
    } catch (error) {
      const message = error instanceof TypeError
        ? "Koneksi terputus. Muat ulang untuk memeriksa menu sebelum mencoba lagi."
        : error.message;
      announce(message, true);
      document.getElementById("dialog-error").textContent = message;
      showRecovery(loginUrl);
    } finally {
      saving = false;
      root.removeAttribute("aria-busy");
      document.querySelectorAll(".planner button, .recipe-dialog button").forEach(button => { button.disabled = false; });
      root.dispatchEvent(new CustomEvent("planner:busychange"));
      focusAfterSave?.focus();
    }
  }
  recipeOptions.addEventListener("click", event => {
    const button = event.target.closest("[data-recipe]");
    if (button && recipeOptions.contains(button)) saveMeal(editingSlot, button.dataset.recipe);
  });
  document.querySelectorAll("[data-remove]").forEach(button => button.addEventListener("click", () => saveMeal(button.dataset.remove, "")));
})();

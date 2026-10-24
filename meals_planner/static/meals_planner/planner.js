(() => {
  "use strict";
  const root = document.querySelector(".planner");
  if (!root) return;
  let state = JSON.parse(document.getElementById("planner-state").textContent);
  const recipes = JSON.parse(document.getElementById("planner-recipes").textContent);
  const recipeById = new Map(recipes.map(recipe => [recipe.id, recipe]));
  const tabs = [...document.querySelectorAll("[data-day]")];
  const cards = [...document.querySelectorAll("[data-slot]")];
  const dialog = document.getElementById("recipe-dialog");
  const search = document.getElementById("recipe-search");
  const status = document.getElementById("planner-status");
  const options = [...document.querySelectorAll("[data-recipe]")];
  let selectedDay = Number(root.dataset.selectedDay);
  let editingSlot = null;
  let opener = null;
  let saving = false;
  const navigation = document.querySelector(".planner-nav");
  const activeNavigation = navigation.querySelector(".is-active");
  if (navigation.scrollWidth > navigation.clientWidth) {
    const navBounds = navigation.getBoundingClientRect();
    const activeBounds = activeNavigation.getBoundingClientRect();
    navigation.scrollLeft = activeBounds.left - navBounds.left - (navigation.clientWidth - activeBounds.width) / 2;
  }

  function announce(message, error = false) {
    status.textContent = message;
    status.classList.toggle("is-error", error);
  }

  function render() {
    const meals = state.meals[String(selectedDay)] || {};
    document.getElementById("planner-subtitle").textContent = selectedDay === state.today
      ? "Menu untuk hari ini!" : `Menu untuk hari ${tabs[selectedDay].dataset.name}!`;
    tabs.forEach((tab, index) => {
      tab.classList.toggle("is-selected", index === selectedDay);
      if (index === selectedDay) tab.setAttribute("aria-current", "date");
      else tab.removeAttribute("aria-current");
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
    document.getElementById("shopping-empty").hidden = state.ingredients.length > 0;
    document.getElementById("planner-example").hidden = !state.example;
  }

  function selectDay(day, updateUrl = true) {
    if (saving) return;
    selectedDay = day;
    if (updateUrl) {
      const url = new URL(window.location.href);
      url.searchParams.set("day", day);
      history.pushState(null, "", url);
    }
    announce("");
    render();
  }

  document.querySelectorAll("[data-day], [data-progress-day]").forEach(link => {
    link.addEventListener("click", event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      selectDay(Number(link.dataset.day ?? link.dataset.progressDay));
    });
  });
  window.addEventListener("popstate", () => {
    const rawDay = new URL(window.location.href).searchParams.get("day");
    selectDay(/^[0-6]$/.test(rawDay || "") ? Number(rawDay) : state.today, false);
  });

  function filterRecipes() {
    const query = search.value.trim().toLocaleLowerCase("id-ID");
    options.forEach(option => { option.hidden = !option.dataset.search.includes(query); });
    document.getElementById("recipe-no-results").hidden = options.some(option => !option.hidden);
  }

  document.querySelectorAll("[data-edit]").forEach(button => {
    button.addEventListener("click", () => {
      if (saving) return;
      editingSlot = button.dataset.edit;
      opener = button;
      const card = cards.find(card => card.dataset.slot === editingSlot);
      const hasRecipe = !!state.meals[String(selectedDay)]?.[editingSlot];
      document.getElementById("recipe-dialog-title").textContent = hasRecipe ? "Ganti menu" : "Tambah menu";
      document.getElementById("recipe-dialog-day").textContent = `${tabs[selectedDay].dataset.name} · ${card.dataset.label}`;
      document.getElementById("dialog-error").textContent = "";
      search.value = "";
      filterRecipes();
      dialog.showModal();
      search.focus();
    });
  });
  search.addEventListener("input", filterRecipes);
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
    target?.focus();
    editingSlot = null;
  });

  async function saveMeal(slot, recipe) {
    if (saving) return;
    saving = true;
    document.querySelectorAll(".planner button, .recipe-dialog button").forEach(button => { button.disabled = true; });
    document.getElementById("dialog-error").textContent = "";
    announce("Menyimpan menu...");
    const day = selectedDay;
    let focusAfterSave = null;
    try {
      const response = await fetch(root.dataset.updateUrl, {
        method: "POST",
        headers: {"X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value},
        body: new URLSearchParams({week: state.week, day: String(day), slot, recipe}),
        credentials: "same-origin",
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.error || "Menu belum tersimpan. Muat ulang halaman dan coba lagi.");
      state = data;
      render();
      if (dialog.open) dialog.close();
      announce(recipe ? "Menu tersimpan. Daftar belanja dan progres sudah diperbarui." : "Menu dihapus. Daftar belanja dan progres sudah diperbarui.");
      if (!recipe) focusAfterSave = cards.find(card => card.dataset.slot === slot)?.querySelector(".meal-add");
    } catch (error) {
      const message = error instanceof TypeError ? "Koneksi terputus. Menu belum tersimpan, silakan coba lagi." : error.message;
      announce(message, true);
      document.getElementById("dialog-error").textContent = message;
    } finally {
      saving = false;
      document.querySelectorAll(".planner button, .recipe-dialog button").forEach(button => { button.disabled = false; });
      focusAfterSave?.focus();
    }
  }
  options.forEach(button => button.addEventListener("click", () => saveMeal(editingSlot, button.dataset.recipe)));
  document.querySelectorAll("[data-remove]").forEach(button => button.addEventListener("click", () => saveMeal(button.dataset.remove, "")));
  document.querySelectorAll('.planner-nav a[aria-disabled="true"]').forEach(link => link.addEventListener("click", event => event.preventDefault()));
})();

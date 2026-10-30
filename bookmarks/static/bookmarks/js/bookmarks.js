(() => {
  const DEBOUNCE_MS = 400;
  const MESSAGES = {
    error: "Terjadi kesalahan. Coba lagi.",
    loading: "Memuat resep…",
    searchError: "Gagal memuat resep. Coba lagi.",
    noResults: (query) => `Tidak ada resep untuk "${query}" di ${categoryName}.`,
  };
  const PAGE_BUTTON_CLASS = "rounded-xl px-4 py-3 bg-background-white border-2 border-border-color font-bold cursor-pointer";
  const CURRENT_PAGE_CLASS = "rounded-xl px-4 py-3 border-2 border-brand-green bg-brand-green text-background font-bold";

  const page = document.getElementById("bookmarks-page");
  if (!page) return;

  const cfg = page.dataset;
  const createDialog = document.getElementById("create-category-dialog");
  const renameDialog = document.getElementById("rename-category-dialog");
  const deleteDialog = document.getElementById("delete-category-dialog");
  const removeDialog = document.getElementById("remove-recipe-dialog");

  // Target dialog hapus/ganti nama diisi saat tombol pembukanya diklik
  let renameTarget = null;
  let deleteTarget = null;
  let removeTarget = null;

  function categoryUrl(template, id) {
    return template.replace(/0\/([a-z]+)\/$/, `${id}/$1/`);
  }

  function removeRecipeUrl(categoryId, recipeId) {
    return cfg.removeRecipeUrl.replace(/0\/recipes\/1\//, `${categoryId}/recipes/${recipeId}/`);
  }

  function goToCategory(id) {
    const url = new URL(window.location.href);
    url.searchParams.set("category", id);
    window.location.assign(url);
  }

  async function postJson(url, body = {}) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": cfg.csrf },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    return { ok: response.ok, data };
  }

  function showError(dialog, field, message) {
    const element = dialog.querySelector(`[data-error-for="${field}"]`);
    if (!element) return;
    element.textContent = message || "";
    element.hidden = !message;
  }

  function clearErrors(dialog) {
    for (const element of dialog.querySelectorAll("[data-error-for]")) element.hidden = true;
  }

  function errorMessage(data, field) {
    return data.errors?.[field]?.[0] || data.error || MESSAGES.error;
  }

  function setBusy(button, busy) {
    button.disabled = busy;
    button.classList.toggle("opacity-60", busy);
  }

  function fillCategoryName(dialog, name) {
    for (const element of dialog.querySelectorAll('[data-field="category-name"]')) element.textContent = name;
  }

  // Tombol pembuka dialog tetap memakai commandfor; di sini cukup catat targetnya
  document.addEventListener("click", (event) => {
    const rename = event.target.closest("[data-rename-category]");
    if (rename) {
      renameTarget = rename.dataset.renameCategory;
      renameDialog.querySelector("input[name=name]").value = rename.dataset.categoryName;
      clearErrors(renameDialog);
      return;
    }

    const remove = event.target.closest("[data-delete-category]");
    if (remove) {
      deleteTarget = remove.dataset.deleteCategory;
      fillCategoryName(deleteDialog, remove.dataset.categoryName);
      clearErrors(deleteDialog);
      return;
    }

    const recipe = event.target.closest("[data-remove-recipe]");
    if (recipe) {
      // Tombol berada di dalam tautan kartu, jadi cegah navigasi lalu buka dialognya manual
      event.preventDefault();
      removeTarget = recipe;
      removeDialog.querySelector('[data-field="recipe-name"]').textContent = recipe.dataset.recipeName;
      clearErrors(removeDialog);
      removeDialog.showModal();
      return;
    }

    if (event.target.closest('[commandfor="create-category-dialog"][command="show-modal"]')) {
      createDialog.querySelector("form").reset();
      clearErrors(createDialog);
    }
  });

  function submitName(dialog, url, onSuccess) {
    const form = dialog.querySelector("form");
    const submit = form.querySelector('[type="submit"]');
    form.addEventListener("submit", async (event) => {
      // form method="dialog" akan langsung menutup dialog, jadi cegah sampai server menjawab
      event.preventDefault();
      clearErrors(dialog);
      setBusy(submit, true);
      try {
        const { ok, data } = await postJson(url(), { name: form.elements.name.value });
        if (ok) return onSuccess(data);
        showError(dialog, "name", errorMessage(data, "name"));
      } catch {
        showError(dialog, "name", MESSAGES.error);
      } finally {
        setBusy(submit, false);
      }
    });
  }

  submitName(createDialog, () => cfg.createUrl, (data) => goToCategory(data.category.id));
  submitName(renameDialog, () => categoryUrl(cfg.renameUrl, renameTarget), () => window.location.reload());

  deleteDialog.querySelector("[data-confirm-delete-category]").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    setBusy(button, true);
    try {
      const { ok, data } = await postJson(categoryUrl(cfg.deleteUrl, deleteTarget));
      if (!ok) return showError(deleteDialog, "form", errorMessage(data, "form"));
      // Kalau yang dihapus bukan kategori yang sedang dibuka, cukup muat ulang halaman ini
      if (deleteTarget === cfg.selectedCategory) goToCategory(data.redirect_category);
      else window.location.reload();
    } catch {
      showError(deleteDialog, "form", MESSAGES.error);
    } finally {
      setBusy(button, false);
    }
  });

  removeDialog.querySelector("[data-confirm-remove-recipe]").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    setBusy(button, true);
    try {
      const url = removeRecipeUrl(cfg.selectedCategory, removeTarget.dataset.removeRecipe);
      const { ok, data } = await postJson(url);
      if (!ok) return showError(removeDialog, "form", errorMessage(data, "form"));

      if (data.recipe_count === 0) return window.location.reload();
      for (const count of document.querySelectorAll(`[data-count-for="${cfg.selectedCategory}"]`)) {
        count.textContent = data.recipe_count;
      }
      removeDialog.close();
      // Muat ulang halaman hasil yang sama agar pencarian dan pagination tetap sesuai
      loadRecipes(currentQuery, currentPage);
    } catch {
      showError(removeDialog, "form", MESSAGES.error);
    } finally {
      setBusy(button, false);
    }
  });

  // Pencarian resep di kategori terpilih, mirip pencarian di halaman Temukan Resep
  const searchForm = document.getElementById("bookmark-search");
  const searchInput = searchForm.querySelector('input[type="search"]');
  const section = document.getElementById("recipe-section");
  const status = document.getElementById("recipe-status");
  const grid = document.getElementById("recipe-grid");
  const pagination = document.getElementById("recipe-pagination");
  const cardTemplate = document.getElementById("recipe-card-template");
  const categoryName = document.getElementById("selected-category-heading").textContent.trim();

  let currentQuery = "";
  let currentPage = 1;
  let controller = null;

  function debounce(fn, delay) {
    let timer;
    const debounced = (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), delay);
    };
    debounced.cancel = () => clearTimeout(timer);
    return debounced;
  }

  function showStatus(message) {
    status.textContent = message;
    status.hidden = !message;
  }

  function recipeDetailUrl(id) {
    return cfg.detailUrl.replace(/0\/$/, `${id}/`);
  }

  function renderCards(recipes) {
    const cards = recipes.map((recipe) => {
      const card = cardTemplate.content.cloneNode(true);
      const field = (name) => card.querySelector(`[data-field="${name}"]`);

      field("link").href = recipeDetailUrl(recipe.id);
      field("image").src = recipe.image;
      field("image").alt = recipe.name;
      field("name").textContent = recipe.name;
      field("ingredients").textContent = recipe.ingredients.join(", ");
      field("count").textContent = `${recipe.ingredient_count} bahan`;

      const remove = card.querySelector("[data-remove-recipe]");
      remove.dataset.removeRecipe = recipe.id;
      remove.dataset.recipeName = recipe.name;
      remove.setAttribute("aria-label", `Hapus ${recipe.name} dari kategori`);
      return card;
    });
    grid.replaceChildren(...cards);
  }

  function pageButton(label, page, { ariaLabel, disabled = false, current = false } = {}) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.className = current ? CURRENT_PAGE_CLASS : PAGE_BUTTON_CLASS;
    if (ariaLabel) button.setAttribute("aria-label", ariaLabel);
    if (current) button.setAttribute("aria-current", "page");
    if (disabled) {
      button.disabled = true;
      button.classList.add("opacity-40", "cursor-not-allowed");
    } else if (!current) {
      button.dataset.page = page;
    }
    return button;
  }

  function renderPagination(data) {
    if (data.num_pages <= 1) {
      pagination.replaceChildren();
      pagination.hidden = true;
      return;
    }

    const items = [
      pageButton("‹", data.page - 1, { ariaLabel: "Halaman sebelumnya", disabled: !data.has_previous }),
    ];
    for (const number of data.page_range) {
      if (number === null) {
        const ellipsis = document.createElement("span");
        ellipsis.className = "px-2";
        ellipsis.textContent = "…";
        items.push(ellipsis);
      } else {
        items.push(pageButton(String(number), number, { current: number === data.page }));
      }
    }
    items.push(pageButton("›", data.page + 1, { ariaLabel: "Halaman berikutnya", disabled: !data.has_next }));

    pagination.replaceChildren(...items);
    pagination.hidden = false;
  }

  async function loadRecipes(query, page = 1) {
    query = query.trim();
    currentQuery = query;

    // Batalkan permintaan sebelumnya agar hasil lama tidak menimpa yang baru
    if (controller) controller.abort();
    controller = new AbortController();
    showStatus(MESSAGES.loading);

    try {
      const params = new URLSearchParams({ q: query, page });
      const url = cfg.recipesUrl.replace(/0\/recipes\/$/, `${cfg.selectedCategory}/recipes/`);
      const response = await fetch(`${url}?${params}`, { signal: controller.signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();

      currentPage = data.page;
      renderCards(data.recipes);
      renderPagination(data);
      showStatus(data.count === 0 ? MESSAGES.noResults(query) : "");
    } catch (error) {
      if (error.name === "AbortError") return;
      grid.replaceChildren();
      pagination.replaceChildren();
      pagination.hidden = true;
      showStatus(MESSAGES.searchError);
    }
  }

  // Kategori kosong tidak punya grid, jadi pencarian tidak perlu dipasang
  if (!grid) return;

  const debouncedLoad = debounce((query) => loadRecipes(query), DEBOUNCE_MS);

  searchInput.addEventListener("input", () => debouncedLoad(searchInput.value));

  searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    debouncedLoad.cancel();
    loadRecipes(searchInput.value);
  });

  // Tombol halaman dari server maupun dari renderPagination sama-sama memakai data-page
  pagination.addEventListener("click", (event) => {
    const button = event.target.closest("[data-page]");
    if (!button || button.disabled) return;
    loadRecipes(currentQuery, Number(button.dataset.page));
    section.scrollIntoView({ behavior: "smooth", block: "start" });
  });
})();

(() => {
  const DEBOUNCE_MS = 400;
  const MESSAGES = {
    empty: "Cari bahan atau resep untuk menemukan resep.",
    loading: "Memuat resep…",
    error: "Gagal memuat resep. Coba lagi.",
    allInFridge: "All ingredients are in your fridge",
    loadingCategories: "Memuat kategori…",
    bookmarkError: "Gagal menyimpan resep. Coba lagi.",
    categoriesError: "Gagal memuat kategori. Tutup lalu coba lagi.",
    noResults: (query, ingredients) => {
      const parts = [];
      if (query) parts.push(`"${query}"`);
      if (ingredients.length) parts.push(`dengan ${ingredients.join(", ")}`);
      return `Tidak ada resep untuk ${parts.join(" ")}.`;
    },
  };
  const PAGE_BUTTON_CLASS = "rounded-xl px-4 py-3 bg-background-white border-2 border-border-color font-bold cursor-pointer";
  const CURRENT_PAGE_CLASS = "rounded-xl px-4 py-3 border-2 border-brand-green bg-brand-green text-background font-bold";

  const form = document.getElementById("recipe-search");
  if (!form) return;

  const input = form.querySelector('input[type="search"]');
  const section = document.getElementById("recipe-section");
  const status = document.getElementById("recipe-status");
  const grid = document.getElementById("recipe-grid");
  const pagination = document.getElementById("recipe-pagination");
  const cardTemplate = document.getElementById("recipe-card-template");
  const ingredientList = document.getElementById("fridge-ingredients");
  const apiUrl = form.dataset.apiUrl;
  const detailUrl = form.dataset.detailUrl;

  let currentQuery = "";
  let controller = null;
  const selectedIngredients = new Set();

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

  function clearResults() {
    grid.replaceChildren();
    pagination.replaceChildren();
    pagination.hidden = true;
  }

  function recipeDetailUrl(id) {
    return detailUrl.replace(/0\/$/, `${id}/`);
  }

  function renderMissing(element, missing) {
    if (missing.length === 0) {
      element.textContent = MESSAGES.allInFridge;
      element.classList.add("text-brand-green");
      return;
    }
    const label = document.createElement("span");
    label.className = "font-bold text-brand-red";
    label.textContent = "Missing:";
    element.replaceChildren(label, ` ${missing.join(", ")}`);
  }

  function renderCards(recipes) {
    const cards = recipes.map((recipe) => {
      const card = cardTemplate.content.cloneNode(true);
      const field = (name) => card.querySelector(`[data-field="${name}"]`);

      field("link").href = recipeDetailUrl(recipe.id);
      field("image").src = recipe.image;
      field("image").alt = recipe.name;
      field("name").textContent = recipe.name;
      renderMissing(field("ingredients"), recipe.missing);
      field("count").textContent = `${recipe.ingredient_count} bahan`;

      const bookmark = card.querySelector("[data-bookmark]");
      bookmark.dataset.bookmark = recipe.id;
      bookmark.dataset.recipeName = recipe.name;
      bookmark.setAttribute("aria-pressed", String(recipe.bookmarked));
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
      button.addEventListener("click", () => {
        loadRecipes(currentQuery, page);
        section.scrollIntoView({ behavior: "smooth", block: "start" });
      });
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

    // Cancel the previous request so stale results can't overwrite newer ones
    if (controller) controller.abort();

    const ingredients = [...selectedIngredients];
    if (!query && !ingredients.length) {
      controller = null;
      clearResults();
      showStatus(MESSAGES.empty);
      return;
    }

    controller = new AbortController();
    showStatus(MESSAGES.loading);

    try {
      const params = new URLSearchParams({ q: query, page });
      for (const ingredient of ingredients) params.append("ingredient", ingredient);
      const response = await fetch(`${apiUrl}?${params}`, { signal: controller.signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();

      renderCards(data.recipes);
      renderPagination(data);
      showStatus(data.count === 0 ? MESSAGES.noResults(query, ingredients) : "");
    } catch (error) {
      if (error.name === "AbortError") return;
      clearResults();
      showStatus(MESSAGES.error);
    }
  }

  const debouncedLoad = debounce((query) => loadRecipes(query), DEBOUNCE_MS);

  input.addEventListener("input", () => debouncedLoad(input.value));

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    debouncedLoad.cancel();
    loadRecipes(input.value);
  });

  ingredientList?.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-ingredient]");
    if (!chip) return;

    const selected = chip.getAttribute("aria-pressed") !== "true";
    chip.setAttribute("aria-pressed", String(selected));
    if (selected) selectedIngredients.add(chip.dataset.ingredient);
    else selectedIngredients.delete(chip.dataset.ingredient);

    debouncedLoad.cancel();
    loadRecipes(input.value);
  });

  // Dialog bookmark sengaja tidak bisa ditutup dengan Esc atau klik di luar, hanya lewat Batal/Simpan
  const bookmarkDialog = document.getElementById("bookmark-dialog");
  const bookmarkForm = bookmarkDialog.querySelector("form");
  const bookmarkSubmit = bookmarkForm.querySelector('[type="submit"]');
  const bookmarkField = (name) => bookmarkDialog.querySelector(`[data-field="${name}"]`);
  let bookmarkButton = null;
  let categoriesController = null;

  function bookmarkUrl(template, id) {
    return template.replace(/\/0\//, `/${id}/`);
  }

  function showBookmarkMessage(name, message) {
    const element = bookmarkField(name);
    element.textContent = message;
    element.hidden = !message;
  }

  function renderCategories(categories) {
    const template = bookmarkField("category-template");
    const items = categories.map((category) => {
      const item = template.content.cloneNode(true);
      const checkbox = item.querySelector("input");
      checkbox.value = category.id;
      checkbox.checked = category.selected;
      item.querySelector('[data-field="category-name"]').textContent = category.name;
      return item;
    });
    bookmarkField("categories").replaceChildren(...items);
  }

  async function openBookmarkDialog(button) {
    bookmarkButton = button;
    bookmarkField("recipe-name").textContent = button.dataset.recipeName;
    bookmarkField("categories").replaceChildren();
    showBookmarkMessage("error", "");
    showBookmarkMessage("status", MESSAGES.loadingCategories);
    bookmarkSubmit.disabled = true;
    bookmarkDialog.showModal();

    if (categoriesController) categoriesController.abort();
    categoriesController = new AbortController();
    try {
      const url = bookmarkUrl(bookmarkDialog.dataset.categoriesUrl, button.dataset.bookmark);
      const response = await fetch(url, { signal: categoriesController.signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      renderCategories(data.categories);
      showBookmarkMessage("status", "");
      bookmarkSubmit.disabled = false;
    } catch (error) {
      if (error.name === "AbortError") return;
      showBookmarkMessage("status", MESSAGES.categoriesError);
    }
  }

  function closeBookmarkDialog() {
    if (categoriesController) categoriesController.abort();
    bookmarkDialog.close();
    bookmarkButton = null;
  }

  grid.addEventListener("click", (event) => {
    const button = event.target.closest("[data-bookmark]");
    if (!button) return;
    // Tombol berada di dalam tautan kartu, jadi jangan sampai membuka halaman detail
    event.preventDefault();
    openBookmarkDialog(button);
  });

  // Fallback untuk browser yang belum mendukung closedby="none"
  bookmarkDialog.addEventListener("cancel", (event) => event.preventDefault());

  bookmarkDialog.querySelector("[data-cancel]").addEventListener("click", closeBookmarkDialog);

  bookmarkForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = bookmarkButton;
    const categoryIds = [...bookmarkForm.querySelectorAll('input[name="category"]:checked')].map((input) => Number(input.value));

    showBookmarkMessage("error", "");
    bookmarkSubmit.disabled = true;
    try {
      const response = await fetch(bookmarkUrl(bookmarkDialog.dataset.saveUrl, button.dataset.bookmark), {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": bookmarkDialog.dataset.csrf },
        body: JSON.stringify({ category_ids: categoryIds }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      button.setAttribute("aria-pressed", String(data.bookmarked));
      closeBookmarkDialog();
    } catch {
      showBookmarkMessage("error", MESSAGES.bookmarkError);
    } finally {
      bookmarkSubmit.disabled = false;
    }
  });

  showStatus(MESSAGES.empty);
})();

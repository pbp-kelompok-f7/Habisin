(() => {
  const DEBOUNCE_MS = 400;
  const MESSAGES = {
    empty: "Cari bahan atau resep untuk menemukan resep.",
    loading: "Memuat resep…",
    error: "Gagal memuat resep. Coba lagi.",
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

  showStatus(MESSAGES.empty);
})();

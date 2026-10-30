// Dialog pilih kategori bookmark untuk tombol [data-bookmark], dipakai di halaman Temukan Resep dan detail resep
(() => {
  const MESSAGES = {
    loadingCategories: "Loading categories…",
    bookmarkError: "Failed to save recipe. Try again.",
    categoriesError: "Failed to load categories. Close and try again.",
  };

  // Dialog sengaja tidak bisa ditutup dengan Esc atau klik di luar, hanya lewat Batal/Simpan
  const bookmarkDialog = document.getElementById("bookmark-dialog");
  if (!bookmarkDialog) return;

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

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-bookmark]");
    if (!button) return;
    // Di halaman Temukan Resep tombolnya berada di dalam tautan kartu, jadi jangan sampai membuka halaman detail
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
})();

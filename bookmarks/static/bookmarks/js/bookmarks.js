(() => {
  const MESSAGES = {
    error: "Terjadi kesalahan. Coba lagi.",
  };

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
      removeTarget.closest('[data-field="link"]').remove();
      for (const count of document.querySelectorAll(`[data-count-for="${cfg.selectedCategory}"]`)) {
        count.textContent = data.recipe_count;
      }
      removeDialog.close();
    } catch {
      showError(removeDialog, "form", MESSAGES.error);
    } finally {
      setBusy(button, false);
    }
  });
})();

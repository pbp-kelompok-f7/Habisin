// Tombol "Cook" di detail resep: menambahkan resep ke Saved Meals lalu menggantinya dengan tautan ke sana
(() => {
  const container = document.getElementById("cook-action");
  const button = container?.querySelector("[data-cook-url]");
  if (!button) return;

  const error = container.querySelector("[data-cook-error]");
  const doneTemplate = container.querySelector("template[data-cook-done]");
  const label = button.textContent;

  button.addEventListener("click", async () => {
    button.disabled = true;
    button.textContent = "Adding…";
    error.hidden = true;
    try {
      const response = await fetch(button.dataset.cookUrl, {
        method: "POST",
        headers: { "X-CSRFToken": button.dataset.csrf },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      button.replaceWith(doneTemplate.content.cloneNode(true));
    } catch {
      button.disabled = false;
      button.textContent = label;
      error.hidden = false;
    }
  });
})();

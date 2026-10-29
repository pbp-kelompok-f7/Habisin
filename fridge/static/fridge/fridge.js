(() => {
  'use strict';

  const root = document.getElementById('fridge');
  if (!root) return;

  const cfg = {
    listUrl: root.dataset.listUrl,
    createUrl: root.dataset.createUrl,
    updateUrl: root.dataset.updateUrl,
    deleteUrl: root.dataset.deleteUrl,
    loginUrl: root.dataset.loginUrl,
    csrf: root.dataset.csrf,
  };

  const $ = (selector, ctx = document) => ctx.querySelector(selector);

  const listEl = $('#item-list');
  const emptyEl = $('#empty');
  const emptyAddEl = $('#empty-add');
  const addTopEl = $('#add-top');
  const errorEl = $('#load-error');
  const tabsEl = $('#tabs');
  const searchForm = $('#search-form');
  const searchInput = $('#search');
  const cardTemplate = $('#item-template');
  const toastEl = $('#toast');

  const editDialog = $('#edit-dialog');
  const editForm = $('#edit-form');
  const editSave = $('#edit-save');
  const editTitle = $('#edit-title');
  const deleteDialog = $('#delete-dialog');
  const deleteName = $('#delete-name');
  const deleteConfirm = $('#delete-confirm');
  const deleteError = $('#delete-error');

  const state = {
    tab: root.dataset.tab,
    q: root.dataset.q || '',
    items: JSON.parse($('#initial-items').textContent),
  };
  let editing = null;
  let mode = 'edit'; // 'edit' atau 'add' (dialog yang sama dipakai untuk keduanya)
  let saveLabel = 'Simpan';
  let deleting = null;
  let busy = false;

  // ---------- Helper ----------

  function urlFor(template, id) {
    return template.replace('/0/', `/${id}/`);
  }

  function debounce(fn, ms) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), ms);
    };
  }

  function tabLabel() {
    const tab = $(`[data-tab="${state.tab}"]`, tabsEl);
    return tab ? tab.textContent.trim() : '';
  }

  let toastTimer;
  function toast(message) {
    toastEl.textContent = message;
    toastEl.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toastEl.hidden = true; }, 3000);
  }

  async function api(url, { method = 'GET', body, signal } = {}) {
    const response = await fetch(url, {
      method,
      signal,
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json',
        'X-CSRFToken': cfg.csrf,
        ...(body ? { 'Content-Type': 'application/json' } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (response.status === 401) {
      window.location.href = `${cfg.loginUrl}?next=${encodeURIComponent(window.location.pathname)}`;
      throw new Error('Sesi berakhir.');
    }

    let data = null;
    try { data = await response.json(); } catch (_) { /* respons bukan JSON */ }

    if (!response.ok) {
      const error = new Error((data && data.error) || 'Terjadi kesalahan. Coba lagi.');
      error.status = response.status;
      error.errors = data && data.errors;
      throw error;
    }
    return data;
  }

  // ---------- Tampilan ----------

  function buildCard(item) {
    const node = cardTemplate.content.firstElementChild.cloneNode(true);
    node.dataset.id = item.id;
    // textContent (bukan innerHTML) supaya nama bahan tidak bisa menyisipkan HTML
    $('[data-amount]', node).textContent = `${item.amount} ${item.unit}`;
    $('[data-name]', node).textContent = item.name;
    $('[data-action="edit"]', node).setAttribute('aria-label', `Update ${item.name}`);
    $('[data-action="delete"]', node).setAttribute('aria-label', `Hapus ${item.name}`);
    return node;
  }

  function render() {
    const fragment = document.createDocumentFragment();
    state.items.forEach((item) => fragment.appendChild(buildCard(item)));
    listEl.replaceChildren(fragment);

    const isEmpty = state.items.length === 0;
    const emptyBecauseSearch = isEmpty && Boolean(state.q);

    if (isEmpty) {
      emptyEl.textContent = state.q
        ? `Tidak ada bahan "${state.q}" di ${tabLabel()}.`
        : `Belum ada bahan di ${tabLabel()}.`;
      emptyEl.hidden = false;
    } else {
      emptyEl.hidden = true;
    }

    // Kosong (bukan karena pencarian): hanya tombol tengah yang tampil.
    // Selain itu: hanya tombol kiri atas yang tampil.
    const showCenterAdd = isEmpty && !emptyBecauseSearch;
    emptyAddEl.hidden = !showCenterAdd;
    addTopEl.style.display = showCenterAdd ? 'none' : '';
  }

  function syncUrl() {
    const params = new URLSearchParams();
    if (state.tab !== 'fridge') params.set('tab', state.tab);
    if (state.q) params.set('q', state.q);
    const query = params.toString();
    history.replaceState(null, '', query ? `?${query}` : window.location.pathname);
  }

  // ---------- Ambil data (tanpa reload halaman) ----------

  let controller = null;
  async function loadItems() {
    if (controller) controller.abort(); // batalkan permintaan lama agar hasilnya tidak tertukar
    controller = new AbortController();
    const { signal } = controller;

    listEl.setAttribute('aria-busy', 'true');
    errorEl.hidden = true;
    try {
      const params = new URLSearchParams({ tab: state.tab, q: state.q });
      const data = await api(`${cfg.listUrl}?${params}`, { signal });
      state.items = data.items;
      render();
    } catch (error) {
      if (error.name === 'AbortError') return;
      errorEl.textContent = 'Gagal memuat bahan. Periksa koneksi lalu coba lagi.';
      errorEl.hidden = false;
    } finally {
      if (!signal.aborted) listEl.setAttribute('aria-busy', 'false');
    }
  }

  // ---------- Pencarian ----------

  const runSearch = debounce(() => {
    const next = searchInput.value.trim();
    if (next === state.q) return;
    state.q = next;
    syncUrl();
    loadItems();
  }, 250);

  searchInput.addEventListener('input', runSearch);
  searchForm.addEventListener('submit', (event) => {
    event.preventDefault();
    state.q = searchInput.value.trim();
    syncUrl();
    loadItems();
  });

  // ---------- Tab Fridge / Freezer / Pantry ----------

  function setActiveTab(key) {
    state.tab = key;
    tabsEl.querySelectorAll('[data-tab]').forEach((tab) => {
      if (tab.dataset.tab === key) tab.setAttribute('aria-current', 'page');
      else tab.removeAttribute('aria-current');
    });
  }

  tabsEl.addEventListener('click', (event) => {
    const link = event.target.closest('[data-tab]');
    if (!link) return;
    event.preventDefault();
    if (link.dataset.tab === state.tab) return;

    setActiveTab(link.dataset.tab);
    syncUrl();
    loadItems();
  });

  // ---------- Tambah / Update ----------

  const fields = {
    name: $('#edit-name'),
    amount: $('#edit-amount'),
    unit: $('#edit-unit'),
    place: $('#edit-place'),
  };

  function showFieldError(name, message) {
    const el = $(`[data-error-for="${name}"]`, editForm);
    if (!el) return;
    el.textContent = message;
    el.hidden = false;
  }

  function clearErrors() {
    editForm.querySelectorAll('[data-error-for]').forEach((el) => {
      el.textContent = '';
      el.hidden = true;
    });
  }

  function openAdd() {
    mode = 'add';
    editing = null;
    saveLabel = 'Tambah';
    editTitle.textContent = 'Tambah bahan';
    editSave.textContent = saveLabel;
    clearErrors();
    fields.name.value = '';
    fields.amount.value = '';
    fields.unit.value = 'pcs';
    fields.place.value = state.tab; // lokasi awal = tab yang sedang dibuka
    editDialog.showModal();
    fields.name.focus();
  }

  function openEdit(item) {
    mode = 'edit';
    saveLabel = 'Simpan';
    editTitle.textContent = 'Update bahan';
    editSave.textContent = saveLabel;
    editing = item;
    clearErrors();
    fields.name.value = item.name;
    fields.amount.value = item.amount;
    fields.unit.value = item.unit;
    fields.place.value = item.place;
    editDialog.showModal();
    fields.amount.focus();
    fields.amount.select();
  }

  editForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if ((mode === 'edit' && !editing) || busy) return;

    clearErrors();
    busy = true;
    editSave.disabled = true;
    editSave.textContent = 'Menyimpan...';
    const body = {
      name: fields.name.value,
      amount: fields.amount.value,
      unit: fields.unit.value,
      place: fields.place.value,
    };
    try {
      if (mode === 'add') {
        const { item } = await api(cfg.createUrl, { method: 'POST', body });
        editDialog.close();
        // pastikan bahan baru langsung terlihat: pindah ke tab-nya dan reset pencarian yang tidak cocok
        if (item.place !== state.tab) setActiveTab(item.place);
        if (state.q && !item.name.toLowerCase().includes(state.q.toLowerCase())) {
          state.q = '';
          searchInput.value = '';
        }
        syncUrl();
        toast(`${item.name} ditambahkan.`);
      } else {
        await api(urlFor(cfg.updateUrl, editing.id), { method: 'POST', body });
        editDialog.close();
        toast('Bahan diperbarui.');
      }
      loadItems(); // muat ulang agar urutan, tab, dan hasil pencarian tetap sesuai
    } catch (error) {
      if (error.errors) {
        Object.entries(error.errors).forEach(([field, messages]) => {
          showFieldError(field in fields ? field : '__all__', messages[0]);
        });
      } else if (error.status === 404 && mode === 'edit') {
        editDialog.close();
        toast('Bahan sudah tidak ada.');
        loadItems();
      } else {
        showFieldError('__all__', error.message);
      }
    } finally {
      busy = false;
      editSave.disabled = false;
      editSave.textContent = saveLabel;
    }
  });

  $('#edit-cancel').addEventListener('click', () => editDialog.close());

  // ---------- Hapus ----------

  function openDelete(item) {
    deleting = item;
    deleteName.textContent = item.name;
    deleteError.hidden = true;
    deleteDialog.showModal();
    deleteConfirm.focus();
  }

  deleteConfirm.addEventListener('click', async () => {
    if (!deleting || busy) return;

    busy = true;
    deleteConfirm.disabled = true;
    deleteConfirm.textContent = 'Menghapus...';
    deleteError.hidden = true;
    const target = deleting;
    try {
      await api(urlFor(cfg.deleteUrl, target.id), { method: 'POST' });
      state.items = state.items.filter((item) => item.id !== target.id);
      render();
      deleteDialog.close();
      toast(`${target.name} dihapus.`);
    } catch (error) {
      if (error.status === 404) {
        deleteDialog.close();
        loadItems();
      } else {
        deleteError.textContent = error.message;
        deleteError.hidden = false;
      }
    } finally {
      busy = false;
      deleteConfirm.disabled = false;
      deleteConfirm.textContent = 'Hapus';
    }
  });

  $('#delete-cancel').addEventListener('click', () => deleteDialog.close());

  // ---------- Klik tombol di kartu, dialog ----------

  listEl.addEventListener('click', (event) => {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    const card = button.closest('li');
    const item = state.items.find((entry) => String(entry.id) === card.dataset.id);
    if (!item) return;
    if (button.dataset.action === 'edit') openEdit(item);
    else openDelete(item);
  });

  document.querySelectorAll('[data-open-add]').forEach((button) => {
    button.addEventListener('click', openAdd);
  });

  // klik area gelap di luar kotak dialog = tutup
  [editDialog, deleteDialog].forEach((dialog) => {
    dialog.addEventListener('click', (event) => {
      if (event.target === dialog) dialog.close();
    });
  });

  render();
})();
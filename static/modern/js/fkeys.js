/* F-keys shortcuts — context-aware (list/form) Vietnamese-accountant style.
 * F2=edit, F3=add/create, F8=save, F9=print, ESC=clear/cancel.
 * Pure vanilla JS, no deps. Mirrors voice-input.js pattern.
 */
(function () {
  'use strict';

  // Skip Django admin
  if (location.pathname.indexOf('/admin/') === 0) return;

  // Inject CSS for row selection highlight
  var css = document.createElement('style');
  css.textContent = '.fkeys-selected { background-color: #fff3cd !important; }';
  document.head.appendChild(css);

  // --- Mode detection ---
  // Form mode = has POST form with submit (data-saving form, not search filter)
  // List mode = has a data table with rows
  function detectMode() {
    if (document.querySelector('form[method="post"] button[type="submit"]')) return 'form';
    if (document.querySelector('table tbody tr')) return 'list';
    return null;
  }

  var mode = detectMode();
  if (!mode) return; // nothing to bind
  document.body.dataset.fkeysMode = mode;

  // --- Bootstrap modal guard ---
  function isModalOpen() {
    return document.querySelector('.modal.show') !== null;
  }

  // --- Button finders (opt-in data-fkeys wins, heuristics fallback) ---
  function findCreateBtn() {
    return document.querySelector('[data-fkeys="create"]')
        || document.querySelector('a[href*="create"]');
  }
  function findSaveBtn() {
    return document.querySelector('[data-fkeys="save"]')
        || document.querySelector('form[method="post"] button[type="submit"]');
  }
  function findCancelBtn() {
    return document.querySelector('[data-fkeys="cancel"]')
        || document.querySelector('a.btn[href*="list"]');
  }
  function findAddLineBtn() {
    var explicit = document.querySelector('[data-fkeys="add-line"]');
    if (explicit) return explicit;
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {
      if (/thêm dòng/i.test(btns[i].textContent)) return btns[i];
    }
    return null;
  }
  function findEditLinkInRow(tr) {
    if (!tr) return null;
    return tr.querySelector('a[href*="detail"]')
        || tr.querySelector('a[href*="update"]')
        || tr.querySelector('[data-fkeys="edit"]');
  }
  function findSelectedRow() {
    return document.querySelector('table tbody tr.fkeys-selected');
  }
  function findFirstRow() {
    return document.querySelector('table tbody tr');
  }
  function findSearchInput() {
    return document.querySelector('input[name="search"]')
        || document.querySelector('input[type="search"]');
  }

  // --- Row selection (click on tbody tr to mark selected) ---
  document.addEventListener('click', function (e) {
    var tr = e.target.closest ? e.target.closest('table tbody tr') : null;
    if (!tr) return;
    var prev = findSelectedRow();
    if (prev && prev !== tr) prev.classList.remove('fkeys-selected');
    tr.classList.add('fkeys-selected');
  });

  // --- Toast (mirrors voice-input.js) ---
  function toast(msg, kind) {
    var el = document.createElement('div');
    el.textContent = msg;
    var bg = kind === 'error' ? '#dc3545' : (kind === 'ok' ? '#28a745' : '#17a2b8');
    el.style.cssText = [
      'position:fixed', 'bottom:20px', 'left:50%', 'transform:translateX(-50%)',
      'background:' + bg, 'color:white', 'padding:10px 18px',
      'border-radius:8px', 'z-index:9999', 'font-size:14px',
      'box-shadow:0 4px 12px rgba(0,0,0,0.2)', 'max-width:90vw'
    ].join(';');
    document.body.appendChild(el);
    setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 2000);
  }

  // --- Key handlers ---
  function onF2() {
    if (mode !== 'list') {
      var firstInput = document.querySelector(
        'input:not([type="hidden"]):not([type="button"]):not([type="submit"]):not([type="checkbox"]):not([type="radio"])'
      );
      if (firstInput) firstInput.focus();
      return;
    }
    var row = findSelectedRow() || findFirstRow();
    if (!row) { toast('Không có dòng để sửa', 'error'); return; }
    var link = findEditLinkInRow(row);
    if (link) {
      toast('Đang mở...');
      link.click();
    } else {
      toast('Không tìm thấy link chi tiết', 'error');
    }
  }

  function onF3() {
    if (mode === 'form') {
      var add = findAddLineBtn();
      if (add) { add.click(); toast('Đã thêm dòng', 'ok'); }
      else toast('Không tìm thấy nút thêm dòng', 'error');
    } else {
      var create = findCreateBtn();
      if (create) {
        toast('Đang mở form tạo...');
        create.click();
      } else toast('Không tìm thấy nút tạo', 'error');
    }
  }

  function onF8() {
    if (mode !== 'form') return; // no-op on list pages
    var save = findSaveBtn();
    if (save) {
      toast('Đang lưu...');
      save.click();
    } else toast('Không tìm thấy nút lưu', 'error');
  }

  function onF9() {
    toast('Đang in...');
    setTimeout(function () { window.print(); }, 200);
  }

  function onEsc() {
    if (mode === 'list') {
      var search = findSearchInput();
      if (search && search.value) {
        search.value = '';
        if (search.form) search.form.submit();
        else search.dispatchEvent(new Event('input', { bubbles: true }));
        toast('Đã xóa tìm kiếm', 'ok');
      }
    } else if (mode === 'form') {
      var cancel = findCancelBtn();
      if (cancel) {
        toast('Đang hủy...');
        cancel.click();
      }
    }
  }

  // --- Bind keydown (capture phase — beats page handlers) ---
  document.addEventListener('keydown', function (e) {
    // Skip inside contenteditable
    if (e.target.isContentEditable) return;
    // Skip when modifier keys held (let browser/OS shortcuts work)
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    // Skip when Bootstrap modal is open (modal has its own ESC handler)
    if (isModalOpen()) return;

    var key = e.key;
    if (key === 'F2') { e.preventDefault(); onF2(); }
    else if (key === 'F3') { e.preventDefault(); onF3(); }
    else if (key === 'F8') { e.preventDefault(); onF8(); }
    else if (key === 'F9') { e.preventDefault(); onF9(); }
    else if (key === 'Escape') { onEsc(); /* no preventDefault — browser may clear input */ }
  }, true);
})();

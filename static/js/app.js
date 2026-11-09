// Genel arayüz davranışları
document.addEventListener('DOMContentLoaded', function () {
  // Seçim değişince formu otomatik gönder (filtreler, hızlı durum değişimi, todo checkbox)
  document.querySelectorAll('.auto-submit, .auto-submit-check').forEach(function (el) {
    el.addEventListener('change', function () { el.form.submit(); });
  });

  // Tema değiştirici
  document.querySelectorAll('.theme-toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var root = document.documentElement;
      var next = root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-bs-theme', next);
      try { localStorage.setItem('tt-theme', next); } catch (e) {}
      document.dispatchEvent(new CustomEvent('themechange'));
    });
  });

  // Toplu seçim
  var checkAll = document.getElementById('checkAll');
  var rowChecks = document.querySelectorAll('.row-check');
  var selCount = document.getElementById('selCount');
  var bulkBtn = document.getElementById('bulkBtn');
  function updateSel() {
    var n = document.querySelectorAll('.row-check:checked').length;
    if (selCount) selCount.textContent = n;
    if (bulkBtn) bulkBtn.disabled = n === 0;
    if (checkAll) {
      checkAll.checked = n > 0 && n === rowChecks.length;
      checkAll.indeterminate = n > 0 && n < rowChecks.length;
    }
  }
  if (checkAll) {
    checkAll.addEventListener('change', function () {
      rowChecks.forEach(function (c) { c.checked = checkAll.checked; });
      updateSel();
    });
  }
  rowChecks.forEach(function (c) { c.addEventListener('change', updateSel); });

  // Excel dosya seçimi + sürükle bırak (sayfadaki her .drop-zone için; çoklu dosya destekli)
  document.querySelectorAll('.drop-zone').forEach(function (zone) {
    var input = zone.querySelector('input[type=file]');
    var label = zone.querySelector('.fw-medium');
    if (!input) return;
    function showNames(files) {
      if (!label || !files.length) return;
      var names = Array.prototype.map.call(files, function (f) { return f.name; });
      label.textContent = names.length > 1 ? names.length + ' dosya seçildi: ' + names.join(', ') : names[0];
    }
    input.addEventListener('change', function () { showNames(input.files); });
    ['dragenter', 'dragover'].forEach(function (ev) {
      zone.addEventListener(ev, function (e) { e.preventDefault(); zone.classList.add('dragover'); });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
      zone.addEventListener(ev, function (e) { e.preventDefault(); zone.classList.remove('dragover'); });
    });
    zone.addEventListener('drop', function (e) {
      if (!e.dataTransfer.files.length) return;
      if (!input.multiple && e.dataTransfer.files.length > 1) {
        var dt = new DataTransfer(); dt.items.add(e.dataTransfer.files[0]); input.files = dt.files;
      } else {
        input.files = e.dataTransfer.files;
      }
      showNames(input.files);
    });
  });

  // Yükleme sürerken düğmeyi kilitle
  var importForm = document.getElementById('suiteImportForm');
  if (importForm) {
    importForm.addEventListener('submit', function () {
      var btn = document.getElementById('suiteImportBtn');
      if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> İçe aktarılıyor…'; }
    });
  }

  // Excel eşleştirme: yeni paket adı alanını sadece gerektiğinde göster
  var suiteSelect = document.getElementById('suiteSelect');
  var newSuiteName = document.getElementById('newSuiteName');
  if (suiteSelect && newSuiteName) {
    var sync = function () { newSuiteName.style.display = suiteSelect.value === 'new' ? '' : 'none'; };
    suiteSelect.addEventListener('change', sync);
    sync();
  }
});

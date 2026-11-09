// Kanban sürükle-bırak (HTML5 Drag and Drop). Dokunmatik cihazlarda kart menüsündeki "Taşı" kullanılır.
(function () {
  var board = document.getElementById('kanban');
  if (!board) return;
  var url = board.dataset.reorderUrl;
  var dragged = null;
  var sourceList = null;

  board.addEventListener('dragstart', function (e) {
    var card = e.target.closest('.kanban-card');
    if (!card) return;
    dragged = card;
    sourceList = card.parentElement;
    card.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', card.dataset.id);
  });

  board.addEventListener('dragend', function () {
    if (dragged) dragged.classList.remove('dragging');
    board.querySelectorAll('.kanban-list.drag-over').forEach(function (l) { l.classList.remove('drag-over'); });
    dragged = null;
  });

  function afterElement(list, y) {
    var cards = Array.prototype.slice.call(list.querySelectorAll('.kanban-card:not(.dragging)'));
    var closest = null, closestOffset = Number.NEGATIVE_INFINITY;
    cards.forEach(function (c) {
      var box = c.getBoundingClientRect();
      var offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closestOffset) { closestOffset = offset; closest = c; }
    });
    return closest;
  }

  board.querySelectorAll('.kanban-list').forEach(function (list) {
    list.addEventListener('dragover', function (e) {
      if (!dragged) return;
      e.preventDefault();
      list.classList.add('drag-over');
      var after = afterElement(list, e.clientY);
      if (after) list.insertBefore(dragged, after); else list.appendChild(dragged);
    });
    list.addEventListener('dragleave', function (e) {
      if (!list.contains(e.relatedTarget)) list.classList.remove('drag-over');
    });
    list.addEventListener('drop', function (e) {
      e.preventDefault();
      list.classList.remove('drag-over');
      if (!dragged) return;
      var title = dragged.querySelector('.kanban-title');
      if (title) title.classList.toggle('is-done', list.dataset.status === 'done');
      var lists = [list];
      if (sourceList && sourceList !== list) lists.push(sourceList);
      save(lists);
    });
  });

  function save(lists) {
    // Sıralı gönder: son yanıttaki sayaçlar tüm değişiklikleri yansıtsın
    var chain = Promise.resolve(null);
    lists.forEach(function (list) {
      var ids = Array.prototype.map.call(list.querySelectorAll('.kanban-card'), function (c) { return c.dataset.id; });
      chain = chain.then(function () {
        return fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: list.dataset.status, ids: ids })
        }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
      });
    });
    chain.then(function (last) {
      var counts = last.counts;
      Object.keys(counts).forEach(function (s) {
        var el = board.querySelector('[data-count-for="' + s + '"]');
        if (el) el.textContent = counts[s];
      });
    }).catch(function () {
      var t = document.getElementById('kanbanToast');
      if (t && window.bootstrap) new bootstrap.Toast(t).show();
      setTimeout(function () { location.reload(); }, 1500);
    });
  }
})();

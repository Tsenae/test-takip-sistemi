// Dashboard grafikleri (Chart.js)
(function () {
  var D = window.DASHBOARD_DATA;
  if (!D || typeof Chart === 'undefined') return;
  var charts = [];

  function css(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  // Durum renkleri temaya göre CSS değişkenlerinden (--st-*) okunur
  function statusColor(key) { return css('--st-' + key); }

  function pct(v, total) {
    return total ? (v / total * 100).toFixed(1).replace('.', ',') + '%' : '0%';
  }

  function stackedDatasets(rows) {
    var surface = css('--card-bg');
    return D.statusOrder.map(function (key) {
      return {
        label: D.statusLabels[key],
        data: rows.map(function (r) { return r[key]; }),
        backgroundColor: statusColor(key),
        borderColor: surface,
        borderWidth: { top: 0, bottom: 0, left: 1, right: 1 },
        borderSkipped: false,
        borderRadius: 3,
        maxBarThickness: 22
      };
    });
  }

  function stackedTooltip(rows) {
    return {
      callbacks: {
        label: function (ctx) {
          var total = rows[ctx.dataIndex].total;
          return ' ' + ctx.dataset.label + ': ' + ctx.parsed[ctx.chart.options.indexAxis === 'y' ? 'x' : 'y'] +
                 ' (' + pct(ctx.raw, total) + ')';
        },
        footer: function (items) {
          var r = rows[items[0].dataIndex];
          return 'Toplam: ' + r.total + ' · Tamamlanma: %' + r.completion + ' · Başarı: %' + r.success;
        }
      }
    };
  }

  function build() {
    charts.forEach(function (c) { c.destroy(); });
    charts = [];
    var ink = css('--chart-ink');
    var grid = css('--chart-grid');
    var surface = css('--card-bg');
    Chart.defaults.color = ink;
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.pointStyle = 'rectRounded';

    // 1) Durum dağılımı (halka)
    var statusEl = document.getElementById('statusChart');
    if (statusEl) {
      var s = D.stats;
      charts.push(new Chart(statusEl, {
        type: 'doughnut',
        data: {
          labels: D.statusOrder.map(function (k) { return D.statusLabels[k] + ' (' + s[k] + ')'; }),
          datasets: [{
            data: D.statusOrder.map(function (k) { return s[k]; }),
            backgroundColor: D.statusOrder.map(statusColor),
            borderColor: surface,
            borderWidth: 2,
            hoverOffset: 6
          }]
        },
        options: {
          maintainAspectRatio: false,
          cutout: '62%',
          plugins: {
            legend: { position: 'bottom' },
            tooltip: {
              callbacks: {
                label: function (ctx) { return ' ' + D.statusLabels[D.statusOrder[ctx.dataIndex]] + ': ' + ctx.raw + ' (' + pct(ctx.raw, s.total) + ')'; }
              }
            }
          }
        },
        plugins: [{
          id: 'centerText',
          afterDraw: function (chart) {
            var area = chart.chartArea;
            if (!area) return;
            var ctx = chart.ctx;
            var cx = (area.left + area.right) / 2, cy = (area.top + area.bottom) / 2;
            ctx.save();
            ctx.textAlign = 'center';
            ctx.fillStyle = css('--bs-body-color') || ink;
            ctx.font = '800 22px Montserrat, ' + Chart.defaults.font.family;
            ctx.fillText('%' + s.completion, cx, cy + 2);
            ctx.fillStyle = ink;
            ctx.font = '12px ' + Chart.defaults.font.family;
            ctx.fillText('tamamlandı', cx, cy + 20);
            ctx.restore();
          }
        }]
      }));
    }

    var axisCommon = {
      grid: { color: grid, drawTicks: false },
      border: { display: false },
      ticks: { padding: 6, precision: 0 }
    };

    // 2) Paket bazında (yatay yığılmış)
    var suiteEl = document.getElementById('suiteChart');
    if (suiteEl) {
      charts.push(new Chart(suiteEl, {
        type: 'bar',
        data: { labels: D.suites.map(function (r) { return r.name; }), datasets: stackedDatasets(D.suites) },
        options: {
          indexAxis: 'y',
          maintainAspectRatio: false,
          interaction: { mode: 'index', axis: 'y', intersect: false },
          scales: {
            x: Object.assign({ stacked: true, beginAtZero: true }, axisCommon),
            y: { stacked: true, grid: { display: false }, border: { display: false } }
          },
          plugins: { legend: { position: 'top', align: 'end' }, tooltip: stackedTooltip(D.suites) }
        }
      }));
    }

    // 3) Modül bazında (dikey yığılmış)
    var moduleEl = document.getElementById('moduleChart');
    if (moduleEl) {
      charts.push(new Chart(moduleEl, {
        type: 'bar',
        data: { labels: D.modules.map(function (r) { return r.name; }), datasets: stackedDatasets(D.modules) },
        options: {
          maintainAspectRatio: false,
          interaction: { mode: 'index', axis: 'x', intersect: false },
          scales: {
            x: { stacked: true, grid: { display: false }, border: { display: false } },
            y: Object.assign({ stacked: true, beginAtZero: true }, axisCommon)
          },
          plugins: { legend: { position: 'top', align: 'end' }, tooltip: stackedTooltip(D.modules) }
        }
      }));
    }
  }

  build();
  document.addEventListener('themechange', build);
  // Web yazı tipleri (Inter/Montserrat) yüklenince ölçüler değişir; açıklamalar doğru yerleşsin diye yeniden çiz
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(build);
})();

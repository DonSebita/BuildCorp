/* Dashboard por rol: todo llega desde /api/v1/dashboard/resumen/. */
(function () {
  "use strict";
  const { api, clp, num, fecha, fechaHora, esc, timbre, vacio } = window.BC;
  const raiz = document.getElementById("dashboard");
  if (!raiz) return;

  const ICONOS = { CRITICO: "bi-exclamation-octagon-fill", WARNING: "bi-exclamation-triangle-fill", INFO: "bi-info-circle-fill" };

  function celda(col, valor) {
    switch (col.tipo) {
      case "folio":
      case "enlace":
        return valor?.url
          ? `<a class="${col.tipo === "folio" ? "folio" : ""}" href="${esc(valor.url)}">${esc(valor.texto)}</a>`
          : esc(valor?.texto ?? valor);
      case "timbre":
        return timbre(valor.estado, valor.texto);
      case "fecha":
        return `<span class="num text-nowrap">${fecha(valor)}</span>`;
      case "fechahora":
        return `<span class="num text-nowrap">${fechaHora(valor)}</span>`;
      case "clp":
        return `<span class="num">${clp(valor)}</span>`;
      case "accion":
        return valor ? `<a class="btn btn-sm btn-outline-primary" href="${esc(valor.url)}">${esc(valor.texto)}</a>` : "";
      default:
        return esc(valor ?? "—");
    }
  }

  function tabla(t) {
    const cabeza = t.columnas.map((c) => `<th${c.tipo === "clp" ? ' class="text-end"' : ""}>${esc(c.titulo)}</th>`).join("");
    const filas = t.filas
      .map((f) => `<tr>${t.columnas.map((c) => `<td${c.tipo === "clp" ? ' class="text-end"' : c.tipo === "accion" ? ' class="text-end"' : ""}>${celda(c, f[c.clave])}</td>`).join("")}</tr>`)
      .join("");
    return `
      <section class="hoja">
        <div class="hoja-cabeza"><h2>${esc(t.titulo)}</h2>${t.enlace ? `<a href="${esc(t.enlace)}">Ver todo</a>` : ""}</div>
        ${t.filas.length ? `<div class="tabla-scroll"><table class="table table-hover"><thead><tr>${cabeza}</tr></thead><tbody>${filas}</tbody></table></div>` : vacio(t.vacio, "bi-check2-circle")}
      </section>`;
  }

  function kpis(lista) {
    return lista
      .map((k) => {
        const valor = k.formato === "clp" ? clp(k.valor) : num(k.valor);
        const etiqueta = k.critico ? `${esc(k.etiqueta)} · requiere acción` : esc(k.etiqueta);
        const tag = k.enlace ? "a" : "div";
        return `<${tag} class="kpi${k.critico ? " critico" : ""}"${k.enlace ? ` href="${esc(k.enlace)}"` : ""}>
          <span class="kpi-valor" title="${esc(valor)}">${valor}</span><span class="kpi-etiqueta">${etiqueta}</span></${tag}>`;
      })
      .join("");
  }

  function alertas(lista, url) {
    const items = lista.length
      ? lista
          .map((a) => {
            const tag = a.enlace ? "a" : "div";
            return `<${tag} class="alerta-item ${a.nivel}"${a.enlace ? ` href="${esc(a.enlace)}"` : ""}>
              <i class="bi ${ICONOS[a.nivel]}" aria-hidden="true"></i>
              <div><strong>${esc(a.tipo)} · ${fechaHora(a.fecha)}</strong><p>${esc(a.mensaje)}</p></div></${tag}>`;
          })
          .join("")
      : vacio("Sin alertas abiertas.", "bi-check2-circle");
    return `<section class="hoja"><div class="hoja-cabeza"><h2>Alertas</h2><a href="${url}">Bandeja</a></div>${items}</section>`;
  }

  function grafico(g) {
    const lienzo = document.getElementById("grafico");
    if (!g || !lienzo || !window.Chart) return;
    lienzo.closest(".hoja").querySelector("h2").textContent = g.titulo;
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.color = "#57547a";
    const dinero = g.formato === "clp";
    // Montos: barras verticales por mes. Conteos: barras horizontales por estado.
    const eje = dinero ? "y" : "x";
    const escalas = {
      [eje]: {
        beginAtZero: true,
        grid: { color: "#ecebf2" },
        border: { display: false },
        ticks: { precision: 0, callback: (v) => (dinero ? (v >= 1e6 ? `$${num(v / 1e6)} M` : clp(v)) : num(v)) },
      },
      [dinero ? "x" : "y"]: { grid: { display: false }, border: { color: "#dddbe8" } },
    };
    new Chart(lienzo, {
      type: "bar",
      data: { labels: g.etiquetas, datasets: [{ data: g.valores, backgroundColor: g.colores, borderRadius: 4, maxBarThickness: 40 }] },
      options: {
        indexAxis: dinero ? "x" : "y",
        maintainAspectRatio: false,
        animation: { duration: 500, easing: "easeOutQuart" },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (c) => (dinero ? clp(c.raw) : `${num(c.raw)} activos`) } },
        },
        scales: escalas,
      },
    });
  }

  async function cargar() {
    try {
      const d = await api(raiz.dataset.api);
      document.getElementById("kpis").innerHTML = kpis(d.kpis);
      document.getElementById("tablas").innerHTML = d.tablas.map(tabla).join("");
      document.getElementById("alertas").innerHTML = alertas(d.alertas, raiz.dataset.alertas);
      const zonaGrafico = document.getElementById("zona-grafico");
      if (d.grafico) {
        zonaGrafico.hidden = false;
        grafico(d.grafico);
      } else {
        zonaGrafico.remove();
      }
    } catch (e) {
      document.getElementById("tablas").innerHTML = `<div class="aviso error"><i class="bi bi-exclamation-octagon"></i><div>No se pudo cargar el panel: ${esc(e.message)} <button class="btn btn-sm btn-outline-primary ms-2" onclick="location.reload()">Reintentar</button></div></div>`;
      document.getElementById("kpis").innerHTML = "";
    }
  }
  cargar();
})();

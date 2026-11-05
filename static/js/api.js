/* Utilidades comunes: fetch con CSRF, formato CLP/fechas, timbres y avisos. */
(function () {
  "use strict";

  function cookie(nombre) {
    const par = document.cookie.split("; ").find((c) => c.startsWith(nombre + "="));
    return par ? decodeURIComponent(par.split("=")[1]) : "";
  }

  function mensajeDeError(datos, status) {
    if (!datos) return `Error ${status}. Intenta de nuevo.`;
    if (typeof datos === "string") return datos;
    if (datos.detail) return Array.isArray(datos.detail) ? datos.detail.join(" ") : datos.detail;
    const partes = [];
    for (const [campo, valor] of Object.entries(datos)) {
      const texto = Array.isArray(valor) ? valor.join(" ") : typeof valor === "object" ? JSON.stringify(valor) : valor;
      partes.push(campo === "non_field_errors" ? texto : `${campo}: ${texto}`);
    }
    return partes.join(" · ") || `Error ${status}.`;
  }

  /** api("/api/v1/activos/", {method: "POST", body: {...}}) → JSON o lanza Error con mensaje legible. */
  async function api(url, opciones = {}) {
    const metodo = (opciones.method || "GET").toUpperCase();
    const cabeceras = { Accept: "application/json" };
    let cuerpo;
    if (opciones.body !== undefined) {
      cabeceras["Content-Type"] = "application/json";
      cuerpo = JSON.stringify(opciones.body);
    }
    if (metodo !== "GET") cabeceras["X-CSRFToken"] = cookie("csrftoken");
    let resp;
    try {
      resp = await fetch(url, { method: metodo, headers: cabeceras, body: cuerpo, credentials: "same-origin" });
    } catch (e) {
      throw new Error("Sin conexión con el servidor. Revisa la red y vuelve a intentar.");
    }
    const tipo = resp.headers.get("Content-Type") || "";
    const datos = tipo.includes("json") ? await resp.json().catch(() => null) : null;
    if (resp.status === 403) throw new Error(datos?.detail || "Tu rol no tiene permiso para esta acción.");
    if (!resp.ok) throw new Error(mensajeDeError(datos, resp.status));
    return datos;
  }

  const fmtCLP = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 });
  const fmtNum = new Intl.NumberFormat("es-CL");
  const fmtFecha = new Intl.DateTimeFormat("es-CL", { day: "2-digit", month: "2-digit", year: "numeric" });
  const fmtFechaHora = new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

  const clp = (n) => (n === null || n === undefined || n === "" ? "—" : fmtCLP.format(Number(n)));
  const num = (n) => (n === null || n === undefined || n === "" ? "—" : fmtNum.format(Number(n)));
  function fecha(iso) {
    if (!iso) return "—";
    const [a, m, d] = iso.slice(0, 10).split("-").map(Number);
    return fmtFecha.format(new Date(a, m - 1, d));
  }
  const fechaHora = (iso) => (iso ? fmtFechaHora.format(new Date(iso)) : "—");

  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const CLASES = {
    DISPONIBLE: "ok", EN_USO: "uso", MANTENIMIENTO: "warn", DADO_DE_BAJA: "baja",
    BORRADOR: "info", ENTREGADO: "uso", ATRASADO: "crit", DEVUELTO: "ok", CERRADO: "cerrado",
    ACTIVO: "ok", BLOQUEADO: "crit", PENDIENTE: "warn", PAGADO: "ok",
    VENCIDO: "crit", PROXIMO: "warn", AL_DIA: "ok", CRITICO: "crit", WARNING: "warn", INFO: "info",
  };
  const timbre = (estado, texto) => `<span class="timbre timbre-${CLASES[estado] || "info"}">${esc(texto || estado)}</span>`;

  function aviso(texto, tipo = "success") {
    const zona = document.getElementById("toasts");
    if (!zona) return alert(texto);
    const el = document.createElement("div");
    const icono = { success: "bi-check-circle", error: "bi-exclamation-octagon", warning: "bi-exclamation-triangle" }[tipo] || "bi-info-circle";
    el.className = `aviso ${tipo}`;
    el.setAttribute("role", tipo === "error" ? "alert" : "status");
    el.innerHTML = `<i class="bi ${icono}"></i><div>${esc(texto)}</div>`;
    zona.appendChild(el);
    setTimeout(() => el.remove(), tipo === "error" ? 9000 : 5000);
  }

  /** Marca un botón como ocupado mientras corre la promesa. */
  async function ocupado(boton, fn) {
    if (!boton) return fn();
    boton.setAttribute("aria-busy", "true");
    boton.disabled = true;
    try {
      return await fn();
    } finally {
      boton.removeAttribute("aria-busy");
      boton.disabled = false;
    }
  }

  function vacio(texto, icono = "bi-inbox") {
    return `<div class="vacio"><i class="bi ${icono}"></i>${esc(texto)}</div>`;
  }

  /** Copia los títulos de columna a cada celda para apilar las tablas en celular. */
  function etiquetar(raiz = document) {
    raiz.querySelectorAll("table.table").forEach((t) => {
      const titulos = [...t.querySelectorAll("thead th")].map((th) => th.textContent.replace(/[↑↓]/g, "").trim());
      if (!titulos.length) return;
      t.classList.add("table-apilada");
      t.querySelectorAll("tbody tr").forEach((tr) =>
        [...tr.children].forEach((td, i) => {
          if (td.hasAttribute("colspan")) return;
          if (titulos[i]) td.dataset.label = titulos[i];
          else td.classList.add("celda-accion");
        })
      );
    });
  }
  document.addEventListener("DOMContentLoaded", () => {
    etiquetar();
    let pendiente;
    new MutationObserver(() => {
      clearTimeout(pendiente);
      pendiente = setTimeout(() => etiquetar(), 30);
    }).observe(document.body, { childList: true, subtree: true });
  });

  window.BC = { api, clp, num, fecha, fechaHora, esc, timbre, aviso, ocupado, vacio, etiquetar };
})();

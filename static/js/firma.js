/* Firma digital con signature_pad sobre <canvas>. */
(function () {
  "use strict";

  /** BCFirma.montar(canvas) → { vacia(), imagen(), limpiar() } */
  function montar(canvas) {
    const pad = new SignaturePad(canvas, { penColor: "#1d1b3a", minWidth: 0.8, maxWidth: 2.6, backgroundColor: "rgba(0,0,0,0)" });

    function ajustar() {
      // Ajusta la resolución del canvas a la pantalla (tablets con alta densidad).
      const datos = pad.toData();
      const ratio = Math.max(window.devicePixelRatio || 1, 1);
      canvas.width = canvas.offsetWidth * ratio;
      canvas.height = canvas.offsetHeight * ratio;
      canvas.getContext("2d").scale(ratio, ratio);
      pad.clear();
      pad.fromData(datos);
    }
    window.addEventListener("resize", ajustar);
    ajustar();

    return {
      vacia: () => pad.isEmpty(),
      imagen: () => pad.toDataURL("image/png"),
      limpiar: () => pad.clear(),
    };
  }

  window.BCFirma = { montar };
})();

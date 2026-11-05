/* Escaneo de QR con html5-qrcode.
   Con HTTPS o localhost usa la cámara en vivo; con http://<IP> (EC2 sin certificado)
   usa «tomar foto del QR», que funciona sin HTTPS. Siempre se puede escribir el código. */
(function () {
  "use strict";

  /** Extrae el código de activo de un texto leído: URL de la ficha o el código solo. */
  function codigoDe(texto) {
    const t = String(texto || "").trim();
    const m = t.match(/\/activos\/([A-Za-z0-9]+-\d{4})\/?/) || t.match(/^([A-Za-z0-9]+-\d{4})$/);
    return m ? m[1].toUpperCase() : null;
  }

  /**
   * BCEscaner.montar({ contenedor, alLeer(codigo), soloCodigo })
   * contenedor: elemento donde dibujar el lector.
   */
  function montar({ contenedor, alLeer }) {
    const enVivo = window.isSecureContext && navigator.mediaDevices && window.Html5Qrcode;
    const idLector = `lector-${Math.random().toString(36).slice(2, 8)}`;
    contenedor.innerHTML = `
      <div class="d-grid gap-2">
        ${enVivo ? `<div class="escaner"><div id="${idLector}"></div></div>
          <button type="button" class="btn btn-primary btn-lg" data-accion="camara"><i class="bi bi-camera-video"></i>Activar cámara</button>`
        : `<label class="btn btn-primary btn-lg m-0"><i class="bi bi-camera"></i>Tomar foto del QR
            <input type="file" accept="image/*" capture="environment" hidden data-accion="foto"></label>
           <div id="${idLector}" hidden></div>`}
        <form class="d-flex gap-2" data-accion="manual">
          <input class="form-control" name="codigo" placeholder="O escribe el código: RTM-0004" autocomplete="off" aria-label="Código del activo">
          <button class="btn btn-outline-primary" type="submit">Buscar</button>
        </form>
        <p class="small text-secondary m-0" data-estado></p>
      </div>`;
    const estado = contenedor.querySelector("[data-estado]");
    const entregar = (texto) => {
      const codigo = codigoDe(texto);
      if (!codigo) {
        estado.textContent = "El QR no corresponde a un activo de BuildCorp.";
        return false;
      }
      estado.textContent = `Leído: ${codigo}`;
      alLeer(codigo);
      return true;
    };

    contenedor.querySelector('[data-accion="manual"]').addEventListener("submit", (e) => {
      e.preventDefault();
      entregar(e.target.codigo.value);
      e.target.reset();
    });

    if (enVivo) {
      const lector = new Html5Qrcode(idLector);
      const boton = contenedor.querySelector('[data-accion="camara"]');
      let activo = false;
      boton.addEventListener("click", async () => {
        const marco = contenedor.querySelector(".escaner");
        if (activo) {
          await lector.stop();
          activo = false;
          marco.classList.remove("activo");
          boton.innerHTML = '<i class="bi bi-camera-video"></i>Activar cámara';
          return;
        }
        try {
          marco.classList.add("activo");
          await lector.start({ facingMode: "environment" }, { fps: 10, qrbox: 240 }, (texto) => {
            if (entregar(texto)) {
              lector.pause(true);
              setTimeout(() => lector.resume(), 1500);
            }
          });
          activo = true;
          boton.innerHTML = '<i class="bi bi-stop-circle"></i>Detener cámara';
        } catch (err) {
          marco.classList.remove("activo");
          estado.textContent = "No se pudo abrir la cámara. Revisa el permiso del navegador o escribe el código.";
        }
      });
    } else if (window.Html5Qrcode) {
      const lector = new Html5Qrcode(idLector);
      contenedor.querySelector('[data-accion="foto"]').addEventListener("change", async (e) => {
        const archivo = e.target.files[0];
        if (!archivo) return;
        estado.textContent = "Leyendo la foto…";
        try {
          entregar(await lector.scanFile(archivo, false));
        } catch (err) {
          estado.textContent = "No se encontró un QR en la foto. Acércate más y vuelve a intentar.";
        }
        e.target.value = "";
      });
    }
  }

  window.BCEscaner = { montar, codigoDe };
})();

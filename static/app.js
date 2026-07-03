const searchInput = document.getElementById("searchInput");
const bookCards = Array.from(document.querySelectorAll(".book-card"));
const emptyState = document.getElementById("emptyState");
const cursorGlow = document.querySelector(".cursor-glow");
const bloodRain = document.getElementById("bloodRain");
const pdfFileInput = document.getElementById("pdfFileInput");
const readerLayout = document.getElementById("readerLayout");
const readerFrameWrap = document.getElementById("readerFrameWrap");
const readerExpandButton = document.getElementById("readerExpandButton");
const readerFullscreenButton = document.getElementById("readerFullscreenButton");

if (searchInput) {
  searchInput.addEventListener("input", () => {
    const query = searchInput.value.trim().toLowerCase();
    let visible = 0;

    for (const card of bookCards) {
      const haystack = card.dataset.search || "";
      const matches = !query || haystack.includes(query);
      card.hidden = !matches;
      if (matches) {
        visible += 1;
      }
    }

    emptyState.hidden = visible !== 0;
  });
}

if (cursorGlow) {
  window.addEventListener("pointermove", (event) => {
    document.body.style.setProperty("--pointer-x", `${event.clientX}px`);
    document.body.style.setProperty("--pointer-y", `${event.clientY}px`);
  });
}

bookCards.forEach((card, index) => {
  card.style.setProperty("--stagger", `${index * 35}ms`);
});

if (bloodRain) {
  const spawnDrop = () => {
    const drop = document.createElement("span");
    drop.className = "blood-rain-drop";

    const left = 6 + Math.random() * 86;
    const duration = 3200 + Math.random() * 2600;
    const delay = Math.random() * 300;
    const stem = 18 + Math.random() * 64;
    const size = 9 + Math.random() * 11;

    drop.style.setProperty("--drop-left", `${left}%`);
    drop.style.setProperty("--drop-duration", `${duration}ms`);
    drop.style.setProperty("--drop-delay", `${delay}ms`);
    drop.style.setProperty("--drop-stem", `${stem}px`);
    drop.style.setProperty("--drop-size", `${size}px`);

    bloodRain.appendChild(drop);
    drop.addEventListener("animationend", () => {
      drop.remove();
    });
  };

  const queueDrop = () => {
    spawnDrop();
    const nextDelay = 700 + Math.random() * 1800;
    window.setTimeout(queueDrop, nextDelay);
  };

  for (let index = 0; index < 4; index += 1) {
    window.setTimeout(spawnDrop, index * 420);
  }

  queueDrop();
}

if (pdfFileInput) {
  pdfFileInput.addEventListener("change", () => {
    if (pdfFileInput.files && pdfFileInput.files.length > 0) {
      pdfFileInput.form.submit();
    }
  });
}

if (readerLayout && readerExpandButton) {
  readerExpandButton.addEventListener("click", () => {
    const expanded = readerLayout.classList.toggle("reader-layout-expanded");
    readerExpandButton.textContent = expanded ? "Modo normal" : "Modo amplio";
  });
}

if (readerFrameWrap && readerFullscreenButton) {
  const syncFullscreenLabel = () => {
    const active = document.fullscreenElement === readerFrameWrap;
    readerFullscreenButton.textContent = active ? "Salir pantalla completa" : "Pantalla completa";
  };

  readerFullscreenButton.addEventListener("click", async () => {
    try {
      if (document.fullscreenElement === readerFrameWrap) {
        await document.exitFullscreen();
      } else if (readerFrameWrap.requestFullscreen) {
        await readerFrameWrap.requestFullscreen();
      } else {
        readerLayout?.classList.toggle("reader-layout-expanded");
      }
    } catch (error) {
      readerLayout?.classList.toggle("reader-layout-expanded");
    } finally {
      syncFullscreenLabel();
    }
  });

  document.addEventListener("fullscreenchange", syncFullscreenLabel);
  syncFullscreenLabel();
}

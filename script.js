/* ============================================
   ALBUMIEN LATAUS, 3D-RING JA EMBLA
   ============================================ */

gsap.registerPlugin(Draggable);

(async function () {
  const grid = document.getElementById("albums-grid");
  const ring = document.getElementById("ring");
  const dragger = document.getElementById("dragger");

  try {
    const res = await fetch("albums.json");
    if (!res.ok) throw new Error("albums.json ei latautunut");
    const albums = await res.json();

    if (!albums.length) {
      if (grid) grid.innerHTML = '<p class="loading">No albums found.</p>';
      return;
    }

    /* ============================================
       1. HERO — 3D-ring kaikilla albumeilla
       ============================================ */
    if (ring && dragger) {
      const total = albums.length;
      const anglePerItem = 360 / total;

      // Pieni säde, jotta ring mahtuu näkyviin
      const radius = Math.max(500, total * 20);

      ring.innerHTML = "";

      albums.forEach((album, i) => {
        const angle = i * anglePerItem;

        const img = document.createElement("div");
        img.className = "img";
        img.style.backgroundImage = `url(${album.cover})`;
        img.dataset.title = album.title;
        img.dataset.spotify = album.spotify_url || "";
        img.dataset.bandcamp = album.bandcamp_url || "";
        img.title = album.title;

        img.style.transform = `rotateY(${angle}deg) translateZ(${radius}px)`;
        img.dataset.angle = angle;

        ring.appendChild(img);
      });

      const images = ring.querySelectorAll(".img");
      let xPos = 0;
      let currentRotation = 0;

      gsap.set(ring, { rotationY: currentRotation });

      /* Alkuanimaatio */
      gsap.timeline()
        .set(dragger, { opacity: 0 })
        .from(".img", {
          duration: 1.5,
          y: 200,
          opacity: 0,
          stagger: 0.04,
          ease: "expo",
        });

      /* Parallax */
      function updateParallax() {
        const rot = gsap.getProperty(ring, "rotationY");
        images.forEach((img) => {
          const angle = parseFloat(img.dataset.angle);
          const wrapped = gsap.utils.wrap(0, 360, rot - 180 - angle);
          const bgX = -(wrapped / 360) * 400;
          img.style.backgroundPosition = `${bgX}px 0px`;
        });
      }

      /* Draggable */
      Draggable.create(dragger, {
        onDragStart: (e) => {
          if (e.touches) e.clientX = e.touches[0].clientX;
          xPos = Math.round(e.clientX);
        },
        onDrag: (e) => {
          if (e.touches) e.clientX = e.touches[0].clientX;
          const delta = Math.round(e.clientX) - xPos;
          const rotationDelta = delta * 0.2;

          currentRotation += rotationDelta;
          gsap.set(ring, { rotationY: currentRotation });
          updateParallax();

          xPos = Math.round(e.clientX);
        },
        onDragEnd: () => {
          gsap.set(dragger, { x: 0, y: 0 });
        },
      });

      /* Klikkaus */
      images.forEach((img) => {
        img.addEventListener("click", () => {
          const url = img.dataset.spotify || img.dataset.bandcamp;
          if (url) window.open(url, "_blank", "noopener");
        });
      });
    }

    /* ============================================
       2. MUSIIKKI — Embla Carousel
       ============================================ */
    if (grid) {
      grid.innerHTML = "";

      albums.forEach((album) => {
        const card = document.createElement("div");
        card.className = "card embla__slide";

        const img = document.createElement("img");
        img.className = "card-img";
        img.alt = album.title + " cover";
        img.loading = "lazy";
        if (album.cover) img.src = album.cover;
        card.appendChild(img);

        const body = document.createElement("div");
        body.className = "card-body";

        const title = document.createElement("div");
        title.className = "card-title";
        title.textContent = album.title;
        body.appendChild(title);

        const meta = document.createElement("div");
        meta.className = "card-meta";
        meta.textContent = album.release_date || album.artist || "";
        body.appendChild(meta);

        const links = document.createElement("div");
        links.className = "store-links";

        if (album.spotify_url) {
          const a = document.createElement("a");
          a.className = "spotify";
          a.href = album.spotify_url;
          a.target = "_blank";
          a.rel = "noopener";
          a.textContent = "Spotify";
          links.appendChild(a);
        }

        if (album.bandcamp_url) {
          const a = document.createElement("a");
          a.className = "bandcamp";
          a.href = album.bandcamp_url;
          a.target = "_blank";
          a.rel = "noopener";
          a.textContent = "Bandcamp";
          links.appendChild(a);
        }

        if (links.children.length) body.appendChild(links);

        card.appendChild(body);
        grid.appendChild(card);
      });

      /* Käynnistä Embla */
      const emblaNode = document.getElementById("albums-embla");
      const emblaApi = EmblaCarousel(emblaNode, {
        loop: false,
        align: "start",
        containScroll: "trimSnaps",
        dragFree: false,
        skipSnaps: false,
        slidesToScroll: 1,
      });

      const prevBtn = document.getElementById("scroll-prev");
      const nextBtn = document.getElementById("scroll-next");
      const scrollHint = document.getElementById("scroll-hint");

      function updateButtons() {
        const canPrev = emblaApi.canScrollPrev();
        const canNext = emblaApi.canScrollNext();

        if (prevBtn) prevBtn.disabled = !canPrev;
        if (nextBtn) nextBtn.disabled = !canNext;

        if (scrollHint) {
          scrollHint.style.display = canPrev || canNext ? "flex" : "none";
        }
      }

      if (prevBtn) prevBtn.addEventListener("click", () => emblaApi.scrollPrev());
      if (nextBtn) nextBtn.addEventListener("click", () => emblaApi.scrollNext());

      emblaApi.on("select", updateButtons);
      emblaApi.on("reInit", updateButtons);
      updateButtons();
    }

  } catch (err) {
    console.error(err);
    if (grid) grid.innerHTML = '<p class="loading">Albums could not be loaded.</p>';
  }
})();
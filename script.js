/* ============================================
   ALBUMIEN JA SINGLEJEN LATAUS + 3D-KARUSELLI
   ============================================ */

(async function () {
  const ring = document.getElementById("ring");
  const carousel = document.getElementById("carousel");
  const mpjvGrid = document.getElementById("albums-grid-mpjv");
  const iotaGrid = document.getElementById("albums-grid-iota");

  let albums = [];
  let tracks = [];

  try {
    const [albumsRes, tracksRes] = await Promise.all([
      fetch("albums.json"),
      fetch("tracks.json"),
    ]);

    if (albumsRes.ok) albums = await albumsRes.json();
    if (tracksRes.ok) tracks = await tracksRes.json();
  } catch (err) {
    console.error(err);
    if (mpjvGrid) mpjvGrid.innerHTML = '<p class="loading">Albums could not be loaded.</p>';
    return;
  }

  // Jaa artisteittain
  const mpjvAlbums = albums.filter(a => (a.artist || "MpjV") === "MpjV");
  const mpjvTracks = tracks.filter(t => (t.artist || "MpjV") === "MpjV");
  const iotaAlbums = albums.filter(a => a.artist === "Iota Dra");
  const iotaTracks = tracks.filter(t => t.artist === "Iota Dra");

  const allReleases = [...albums, ...tracks].sort(
    (a, b) => (b.release_date || "").localeCompare(a.release_date || "")
  );

  if (!allReleases.length) return;

  /* ============================================
     1. HERO — 3D-RING-KARUSELLI (kaikki artistit)
     ============================================ */
  if (ring && carousel) {
    const total = allReleases.length;
    const anglePerItem = 360 / total;
    const radius = 1050;

    ring.innerHTML = "";
    allReleases.forEach((item, i) => {
      const angle = i * anglePerItem;

      const slide = document.createElement("div");
      slide.className = "carousel-slide";
      slide.style.backgroundImage = `url("${item.cover}")`;
      slide.style.transform =
        `rotateY(${angle}deg) translateZ(${radius}px)`;
      slide.dataset.url = item.spotify_url || item.bandcamp_url || "";
      slide.title = item.title;

      slide.addEventListener("click", () => {
        if (slide.dataset.url) {
          window.open(slide.dataset.url, "_blank", "noopener");
        }
      });

      ring.appendChild(slide);
    });

    let currentRotation = 0;
    const speed = -0.010;

    function animate() {
      currentRotation += speed;
      ring.style.transform = `rotateY(${currentRotation}deg)`;
      requestAnimationFrame(animate);
    }

    ring.style.transform = `rotateY(${currentRotation}deg)`;
    requestAnimationFrame(animate);
  }

  /* ============================================
     APUFUNKTIO: renderöi kortit gridiin
     ============================================ */
  function renderGrid(gridEl, albumList, trackList) {
    if (!gridEl) return;

    const combined = [
      ...albumList.map((a) => ({ ...a, type: "Album" })),
      ...trackList.map((t) => ({ ...t, type: "Track" })),
    ].sort(
      (a, b) => (b.release_date || "").localeCompare(a.release_date || "")
    );

    gridEl.innerHTML = "";

    combined.forEach((item) => {
      const card = document.createElement("div");
      card.className = "card";

      const img = document.createElement("img");
      img.className = "card-img";
      img.alt = item.title + " cover";
      img.loading = "lazy";
      if (item.cover) img.src = item.cover;
      card.appendChild(img);

      const body = document.createElement("div");
      body.className = "card-body";

      const titleRow = document.createElement("div");
      titleRow.className = "card-title-row";

      const title = document.createElement("div");
      title.className = "card-title";
      title.textContent = item.title;
      titleRow.appendChild(title);

      const badge = document.createElement("span");
      badge.className = "type-badge " + item.type.toLowerCase();
      badge.textContent = item.type;
      titleRow.appendChild(badge);

      body.appendChild(titleRow);

      const meta = document.createElement("div");
      meta.className = "card-meta";
      meta.textContent = item.release_date || "";
      body.appendChild(meta);

      const links = document.createElement("div");
      links.className = "store-links";

      if (item.spotify_url) {
        const a = document.createElement("a");
        a.className = "spotify";
        a.href = item.spotify_url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "Spotify";
        links.appendChild(a);
      }

      if (item.bandcamp_url) {
        const a = document.createElement("a");
        a.className = "bandcamp";
        a.href = item.bandcamp_url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "Bandcamp";
        links.appendChild(a);
      }

      if (links.children.length) body.appendChild(links);

      card.appendChild(body);
      gridEl.appendChild(card);
    });

    gridEl.addEventListener("wheel", (e) => {
      if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
        e.preventDefault();
        gridEl.scrollLeft += e.deltaY * 1.5;
      }
    }, { passive: false });
  }

  /* ============================================
     2. MUSIC — MpjV
     ============================================ */
  renderGrid(mpjvGrid, mpjvAlbums, mpjvTracks);

  /* ============================================
     3. MUSIC — Iota Dra
     ============================================ */
  renderGrid(iotaGrid, iotaAlbums, iotaTracks);

  /* ============================================
     4. HERO — Uusin track (vain MpjV)
     ============================================ */
  const trackLink = document.getElementById("latest-track-link");
  const trackCover = document.getElementById("latest-track-cover");
  const trackTitle = document.getElementById("latest-track-title");
  const trackDate = document.getElementById("latest-track-date");
  const trackLinks = document.getElementById("latest-track-links");

  if (mpjvTracks.length > 0 && trackCover) {
    const latest = mpjvTracks[0];

    trackCover.src = latest.cover || "";
    trackCover.alt = latest.title + " cover";
    trackTitle.textContent = latest.title;
    trackDate.textContent = latest.release_date || "";

    const primaryUrl = latest.spotify_url || latest.bandcamp_url || "#";
    trackLink.href = primaryUrl;

    if (trackLinks) {
      trackLinks.innerHTML = "";

      if (latest.spotify_url) {
        const a = document.createElement("a");
        a.className = "spotify";
        a.href = latest.spotify_url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "Spotify";
        trackLinks.appendChild(a);
      }

      if (latest.bandcamp_url) {
        const a = document.createElement("a");
        a.className = "bandcamp";
        a.href = latest.bandcamp_url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "Bandcamp";
        trackLinks.appendChild(a);
      }
    }
  } else if (trackTitle) {
    trackTitle.textContent = "No tracks yet";
  }

  /* ============================================
     5. HERO — Uusin albumi (vain MpjV)
     ============================================ */
  const albumLink = document.getElementById("latest-album-link");
  const albumCover = document.getElementById("latest-album-cover");
  const albumTitle = document.getElementById("latest-album-title");
  const albumDate = document.getElementById("latest-album-date");
  const albumLinks = document.getElementById("latest-album-links");

  if (mpjvAlbums.length > 0 && albumCover) {
    const latest = mpjvAlbums[0];

    albumCover.src = latest.cover || "";
    albumCover.alt = latest.title + " cover";
    albumTitle.textContent = latest.title;
    albumDate.textContent = latest.release_date || "";

    const primaryUrl = latest.spotify_url || latest.bandcamp_url || "#";
    albumLink.href = primaryUrl;

    if (albumLinks) {
      albumLinks.innerHTML = "";

      if (latest.spotify_url) {
        const a = document.createElement("a");
        a.className = "spotify";
        a.href = latest.spotify_url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "Spotify";
        albumLinks.appendChild(a);
      }

      if (latest.bandcamp_url) {
        const a = document.createElement("a");
        a.className = "bandcamp";
        a.href = latest.bandcamp_url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "Bandcamp";
        albumLinks.appendChild(a);
      }
    }
  }
})();
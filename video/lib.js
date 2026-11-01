/* Shared helpers for every scene. Reads window.DATA and window.BARS from data.js. */
(function () {
  const D = window.DATA;
  const FPS = 30;

  const MOVE = {
    enter: { duration: 0.6, ease: "power2.out" },
    move: { duration: 0.8, ease: "power3.inOut" },
    exit: { duration: 0.4, ease: "power2.in" },
    camera: { duration: 1.2, ease: "power2.inOut" },
    follow: { delay: 0.15 }
  };
  const SEAM = { distance: 260, duration: 0.4 };

  const frames = (n) => n / FPS;
  const snap = (t) => Math.round(t * FPS) / FPS;

  function cssColor(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  /* ---------- the voice is the clock ---------- */
  const clipStarts = [];
  D.narration.reduce((elapsed, seconds) => {
    clipStarts.push(elapsed);
    return elapsed + seconds + D.air;
  }, 0);

  const PUNCTUATION_PAUSE = { ",": 0.18, ":": 0.22, ".": 0.3 };

  function isPausePunctuation(text, index) {
    const ch = text[index];
    if (!(ch in PUNCTUATION_PAUSE)) return false;
    return !(ch === "." && /\d/.test(text[index - 1] || "") && /\d/.test(text[index + 1] || ""));
  }

  function modelTimes(text, seconds) {
    const letters = [...text].filter((ch, i) => !/[\s"]/.test(ch) && !isPausePunctuation(text, i)).length;
    let pauseTotal = 0;
    for (let i = 0; i < text.length; i++) if (isPausePunctuation(text, i)) pauseTotal += PUNCTUATION_PAUSE[text[i]];
    const rate = (seconds - pauseTotal - 0.1) / letters;
    const at = [];
    const pauses = [];
    let t = 0.05;
    for (let i = 0; i < text.length; i++) {
      at[i] = t;
      if (isPausePunctuation(text, i)) {
        pauses.push(t);
        t += PUNCTUATION_PAUSE[text[i]];
      } else if (!/[\s"]/.test(text[i])) {
        t += rate;
      }
    }
    return { at, pauses };
  }

  function correctionCurve(n, pauses, seconds) {
    const knots = [[0, 0]];
    D.pauseAnchors[n - 1].forEach((measured, i) => {
      if (measured != null && pauses[i] != null) knots.push([pauses[i], measured]);
    });
    knots.push([seconds, seconds]);
    return (predicted) => {
      for (let k = 1; k < knots.length; k++) {
        const [p0, m0] = knots[k - 1];
        const [p1, m1] = knots[k];
        if (predicted <= p1) return m0 + ((predicted - p0) / (p1 - p0)) * (m1 - m0);
      }
      return predicted;
    };
  }

  /* Seconds into clip n at which the words of `phrase` start. */
  function clipCue(n, phrase) {
    const text = D.narrationText[n - 1];
    const seconds = D.narration[n - 1];
    const index = text.indexOf(phrase);
    if (index < 0) throw new Error(`cue "${phrase}" not in clip ${n}`);
    const { at, pauses } = modelTimes(text, seconds);
    return correctionCurve(n, pauses, seconds)(at[index]);
  }

  function sceneStart(sceneKey) {
    return clipStarts[D.sceneFirstClip[sceneKey] - 1];
  }

  /* Time, local to the scene file, at which the words of `phrase` in clip n start. */
  function cue(sceneKey, n, phrase) {
    return snap(clipStarts[n - 1] - sceneStart(sceneKey) + (phrase == null ? 0 : clipCue(n, phrase)));
  }

  /* ---------- seams: every cut travels LEFT and lands mid-motion ---------- */
  function seamOut(tl, stage, cutTime) {
    tl.to(stage, { x: -SEAM.distance, duration: SEAM.duration, ease: "power3.in" }, cutTime - SEAM.duration);
  }

  function seamIn(tl, stage) {
    tl.fromTo(stage, { x: SEAM.distance }, { x: 0, duration: SEAM.duration, ease: "power3.out" }, 0);
  }

  /* ---------- text and block entrances ---------- */
  function textIn(tl, target, at, extra) {
    tl.fromTo(
      target,
      { opacity: 0, filter: "blur(8px)" },
      { opacity: 1, filter: "blur(0px)", duration: MOVE.enter.duration, ease: MOVE.enter.ease, ...extra },
      at
    );
  }

  function textOut(tl, target, at) {
    tl.to(target, { opacity: 0, filter: "blur(6px)", duration: MOVE.exit.duration, ease: MOVE.exit.ease }, at);
  }

  function wipeIn(tl, target, at, duration) {
    tl.fromTo(
      target,
      { clipPath: "inset(0 100% 0 0)" },
      { clipPath: "inset(0 0% 0 0)", duration: duration || MOVE.enter.duration, ease: MOVE.enter.ease },
      at
    );
  }

  /* ---------- real frames driving: step through a sprite reel, one PNG every 7.5 video frames ---------- */
  function reelCell(slot, spec) {
    const col = slot % spec.cols;
    const row = Math.floor(slot / spec.cols);
    return `${-col * spec.w}px ${-row * spec.h}px`;
  }

  function driveReel(tl, target, spec) {
    const perSecond = spec.perSecond || 4;
    const first = spec.from || 0;
    const count = spec.count;
    for (let k = 0; k < count; k++) {
      const slot = Math.min(first + k, spec.last != null ? spec.last : first + count - 1);
      tl.set(target, { backgroundPosition: reelCell(slot, spec) }, snap(spec.at + k / perSecond));
    }
  }

  /* ---------- the model's insides: bars drawn from the real activation vectors ---------- */
  function drawBars(canvas, values, orientation) {
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = cssColor("--ink");
    const n = values.length;
    const alongLength = orientation === "column" ? h : w;
    const crossLength = orientation === "column" ? w : h;
    const axis = crossLength * 0.34;
    const step = alongLength / n;
    values.forEach((v, i) => {
      const extent = v >= 0 ? v * (crossLength - axis) : v * axis;
      const start = v >= 0 ? axis : axis + extent;
      const length = Math.abs(extent);
      if (orientation === "column") ctx.fillRect(start, i * step, length, Math.max(step * 0.72, 1));
      else ctx.fillRect(i * step, crossLength - start - length, Math.max(step * 0.72, 1), length);
    });
  }

  /* ---------- the pile of 738 ---------- */
  const PILE = { cols: 41, rows: 18, pitch: 14, size: 12 };

  function seededRandom(seed) {
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function pileRoles() {
    const random = seededRandom(26406);
    const cells = Array.from({ length: D.pool }, (_, i) => i);
    for (let i = cells.length - 1; i > 0; i--) {
      const j = Math.floor(random() * (i + 1));
      [cells[i], cells[j]] = [cells[j], cells[i]];
    }
    const others = D.failures - D.keys.P4 - D.keys.P7 - D.keys.P8;
    let cursor = 0;
    const take = (count) => cells.slice(cursor, (cursor += count));
    const p4 = take(D.keys.P4);
    const p7 = take(D.keys.P7);
    const p8 = take(D.keys.P8);
    const other = take(others);
    return {
      p4,
      p7,
      p8,
      other,
      crashed: [...p4, ...p7, ...p8, ...other],
      foundP4: [...p4.slice(0, D.p4.inKey), ...other.slice(0, D.p4.found - D.p4.inKey)],
      foundP7: p7.slice(0, D.p7.found)
    };
  }

  function buildPile(container) {
    const roles = pileRoles();
    const tiles = [];
    for (let i = 0; i < D.pool; i++) {
      const tile = document.createElement("div");
      tile.className = "tile";
      tile.style.left = `${(i % PILE.cols) * PILE.pitch}px`;
      tile.style.top = `${Math.floor(i / PILE.cols) * PILE.pitch}px`;
      container.appendChild(tile);
      tiles.push(tile);
    }
    return { tiles, roles, ...PILE, width: PILE.cols * PILE.pitch - 2, height: PILE.rows * PILE.pitch - 2 };
  }

  /* Move tiles to a grid on screen. The pile container must hold still (no scale tween) while this plays. */
  function slideToGroup(tl, pile, tileIndexes, pose, group, at, extra) {
    const perRow = group.perRow;
    const grow = group.size / (PILE.size * pose.scale);
    tileIndexes.forEach((index, order) => {
      const col = order % perRow;
      const row = Math.floor(order / perRow);
      const targetX = group.x + col * (group.size + group.gap);
      const targetY = group.y + row * (group.size + group.gap);
      const homeX = pose.x + (index % PILE.cols) * PILE.pitch * pose.scale;
      const homeY = pose.y + Math.floor(index / PILE.cols) * PILE.pitch * pose.scale;
      tl.to(
        pile.tiles[index],
        {
          x: (targetX - homeX) / pose.scale,
          y: (targetY - homeY) / pose.scale,
          scale: grow,
          transformOrigin: "0 0",
          duration: group.duration || MOVE.move.duration + 0.2,
          ease: MOVE.move.ease,
          ...extra
        },
        at + order * (group.stagger != null ? group.stagger : 0.012)
      );
    });
  }

  /* Fill each [data-bind] element from DATA, e.g. data-bind="p4.jaccard" data-decimals="2". */
  function bindNumbers(root) {
    root.querySelectorAll("[data-bind]").forEach((el) => {
      const value = el.dataset.bind.split(".").reduce((o, k) => o[k], D);
      const decimals = el.dataset.decimals;
      el.textContent = decimals != null ? Number(value).toFixed(Number(decimals)) : String(value);
    });
  }

  window.LIB = {
    D, FPS, MOVE, SEAM, PILE, frames, snap, cssColor, cue, clipStarts, sceneStart,
    seededRandom, seamOut, seamIn, textIn, textOut, wipeIn, driveReel, drawBars, buildPile, slideToGroup, bindNumbers
  };
})();

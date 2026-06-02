(function () {
  const DATA = window.EVOLUTION_DATA;
  const nodes = DATA.nodes;
  const edges = DATA.edges;
  const nodeById = new Map(nodes.map((node) => [node.id, node]));

  const LEFT_PANEL_WIDTH = 360;
  const MIN_CANVAS_WIDTH = 1560;
  const MIN_CANVAS_HEIGHT = 860;
  const TOP_PAD = 460;
  const BOTTOM_PAD = 150;
  const HOUR_HEIGHT = 10;
  const TRACK_OFFSET = 46;
  const NODE_WIDTH = 34;
  const PLAYBACK_FRAME_MS = 1000 / 30;
  const IDLE_FRAME_MS = 250;

  const minMs = Date.parse(DATA.startedAt);
  const maxMs = Date.parse(DATA.endsAt);
  const defaultMs = clamp(Date.now(), minMs, maxMs);
  const appOpenedAt = Date.now();

  const root = document.documentElement;
  const hudShell = document.getElementById("hudShell");
  const treeSvg = document.getElementById("treeSvg");
  const trendSvg = document.getElementById("trendSvg");
  const metricList = document.getElementById("metricList");
  const tooltip = document.getElementById("tooltip");
  const timeReadout = document.getElementById("timeReadout");
  const timeSlider = document.getElementById("timeSlider");
  const secretTime = document.getElementById("secretTime");
  const secretPanel = document.getElementById("secretPanel");
  const liveButton = document.getElementById("liveButton");
  const detailButton = document.getElementById("detailButton");
  const detailPanel = document.getElementById("detailPanel");
  const playToggle = document.getElementById("playToggle");
  const restartPlayback = document.getElementById("restartPlayback");
  const speedSelect = document.getElementById("speedSelect");
  const playbackSlider = document.getElementById("playbackSlider");
  const playbackTime = document.getElementById("playbackTime");

  let selectedId = null;
  let manualMode = false;
  let manualMs = defaultMs;
  let liveBaseMs = defaultMs;
  let liveStartedAt = appOpenedAt;
  let lastRenderedSecond = -1;
  let playbackMode = false;
  let playbackBaseMs = minMs;
  let playbackStartedAt = appOpenedAt;
  let playbackSpeed = Number(speedSelect.value || 2880);
  let lastFrameAt = 0;
  let detailOpen = false;

  root.style.setProperty("--sidebar-width", `${LEFT_PANEL_WIDTH}px`);

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function currentMs() {
    if (playbackMode) {
      const elapsed = (Date.now() - playbackStartedAt) * playbackSpeed;
      return clamp(playbackBaseMs + elapsed, minMs, maxMs);
    }
    if (manualMode) return manualMs;
    return clamp(Date.now(), minMs, maxMs);
  }

  function yForTime(ms) {
    return TOP_PAD + ((ms - minMs) / 3600000) * HOUR_HEIGHT;
  }

  function fmtDate(ms) {
    const parts = new Intl.DateTimeFormat("zh-CN", {
      timeZone: "Asia/Shanghai",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    })
      .formatToParts(new Date(ms))
      .reduce((acc, part) => {
        acc[part.type] = part.value;
        return acc;
      }, {});
    return `${parts.year}/${parts.month}/${parts.day} ${parts.hour}:${parts.minute}:${parts.second}`;
  }

  function fmtDuration(ms, compact = false) {
    const totalMinutes = Math.max(0, Math.round(ms / 60000));
    const days = Math.floor(totalMinutes / 1440);
    const hours = Math.floor((totalMinutes % 1440) / 60);
    const minutes = totalMinutes % 60;
    if (days && compact) return `${days}d ${hours}h ${minutes}min`;
    if (days) return `${days}d ${hours}h${minutes}min`;
    return `${hours}h${String(minutes).padStart(2, "0")}min`;
  }

  function fmtAxisDate(ms) {
    const parts = new Intl.DateTimeFormat("zh-CN", {
      timeZone: "Asia/Shanghai",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    })
      .formatToParts(new Date(ms))
      .reduce((acc, part) => {
        acc[part.type] = part.value;
        return acc;
      }, {});
    return {
      date: `${parts.month}/${parts.day}`,
      time: `${parts.hour}:${parts.minute}`,
    };
  }

  function fmtScaleDuration(ms) {
    const totalMinutes = Math.max(1, Math.round(ms / 60000));
    const days = Math.floor(totalMinutes / 1440);
    const hours = Math.floor((totalMinutes % 1440) / 60);
    const minutes = totalMinutes % 60;
    if (days) return `${days}d ${hours}h`;
    if (hours) return `${hours}h ${minutes}min`;
    return `${minutes}min`;
  }

  function statusFor(node, now) {
    if (now < node.startMs) return "future";
    if (now < node.endMs) return "running";
    return "completed";
  }

  function scoreFor(node, now) {
    if (now < node.startMs) return null;
    if (now >= node.endMs) return node.score;
    const progress = clamp((now - node.startMs) / (node.endMs - node.startMs), 0, 1);
    const liveWave = Math.sin(node.index * 1.3 + now / 1800000) * 0.42;
    return clamp(node.startScore + (node.score - node.startScore) * progress + liveWave, 0, 100);
  }

  function visibleNodes(now) {
    return nodes.filter((node) => node.startMs <= now);
  }

  function runningNodes(now) {
    return nodes.filter((node) => node.startMs <= now && now < node.endMs);
  }

  function visibleMaxSequence(now) {
    return visibleNodes(now).reduce((max, node) => Math.max(max, node.sequence), 0);
  }

  function completedNodes(now) {
    return nodes.filter((node) => node.endMs <= now);
  }

  function trackRunningSummary(now) {
    return DATA.tracks
      .map((label, track) => {
        const active = nodes.find((node) => node.track === track && node.startMs <= now && now < node.endMs);
        return `${track + 1}:${active ? `#${active.id}` : "--"}`;
      })
      .join("&nbsp;&nbsp;");
  }

  function updateCanvas(now) {
    const currentY = yForTime(now);
    const maxSequence = visibleMaxSequence(now);
    const viewportWidth = window.innerWidth || MIN_CANVAS_WIDTH;
    const naturalWidth = LEFT_PANEL_WIDTH + 420 + DATA.tracks.length * 210 + maxSequence * TRACK_OFFSET;
    const canvasWidth = Math.max(MIN_CANVAS_WIDTH, viewportWidth - 18, naturalWidth);
    const canvasHeight = Math.max(MIN_CANVAS_HEIGHT, Math.ceil(currentY + BOTTOM_PAD));

    root.style.setProperty("--canvas-width", `${canvasWidth}px`);
    root.style.setProperty("--stage-height", `${canvasHeight}px`);
    hudShell.style.height = `${canvasHeight}px`;

    return {
      totalWidth: canvasWidth,
      stageWidth: canvasWidth - LEFT_PANEL_WIDTH,
      height: canvasHeight,
      currentY,
      maxSequence,
    };
  }

  function trackLayout(stageWidth, maxSequence) {
    const timelineX = stageWidth - 82;
    const plotLeft = 92;
    const plotRight = timelineX - 128;
    const maxShift = maxSequence * TRACK_OFFSET;
    const trackSpan = Math.max(520, plotRight - plotLeft - maxShift);
    const step = trackSpan / DATA.tracks.length;
    const centers = DATA.tracks.map((_, track) => plotLeft + step * (track + 0.5));
    return { centers, timelineX, plotLeft, plotRight };
  }

  function documentBoundsForNodes(focusNodes, now, canvas) {
    if (!focusNodes.length) return null;
    const app = document.querySelector(".app");
    const appLeft = app ? app.offsetLeft : 0;
    const appTop = app ? app.offsetTop : 0;
    const layout = trackLayout(canvas.stageWidth, canvas.maxSequence);
    const positions = focusNodes.map((node) => layoutNode(node, now, layout));
    const xs = positions.flatMap((pos) => [
      appLeft + LEFT_PANEL_WIDTH + pos.x - 13,
      appLeft + LEFT_PANEL_WIDTH + pos.x + pos.width + 13,
    ]);
    const ys = positions.flatMap((pos) => [appTop + pos.y1, appTop + pos.y2]);
    return {
      minX: Math.min(...xs),
      maxX: Math.max(...xs),
      centerX: (Math.min(...xs) + Math.max(...xs)) / 2,
      minY: Math.min(...ys),
      maxY: Math.max(...ys),
      centerY: (Math.min(...ys) + Math.max(...ys)) / 2,
    };
  }

  function focusBounds(now, canvas) {
    const selected = selectedId ? nodeById.get(selectedId) : null;
    if (selected && selected.startMs <= now) return documentBoundsForNodes([selected], now, canvas);
    return documentBoundsForNodes(runningNodes(now), now, canvas);
  }

  function chartBottomInViewport() {
    const rect = trendSvg.getBoundingClientRect();
    if (!rect.width || !rect.height) return 0;
    return rect.bottom;
  }

  function ensureCurrentCapsulesVisible(now, canvas, force = false) {
    const bounds = focusBounds(now, canvas);
    if (!bounds) return;

    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    const chartBottom = chartBottomInViewport();
    const rightPaneWidth = Math.max(480, window.innerWidth - LEFT_PANEL_WIDTH);
    const visibleLeft = scrollX + LEFT_PANEL_WIDTH + 30;
    const visibleRight = scrollX + window.innerWidth - 38;
    const visibleTop = scrollY + Math.max(84, Math.min(window.innerHeight * 0.42, chartBottom + 44));
    const visibleBottom = scrollY + window.innerHeight - 72;

    let nextX = scrollX;
    let nextY = scrollY;
    const desiredScreenX = LEFT_PANEL_WIDTH + rightPaneWidth * 0.52;
    const desiredScreenY = Math.max(chartBottom + 130, window.innerHeight * 0.62);
    const needsX = bounds.minX < visibleLeft || bounds.maxX > visibleRight;
    const needsY = bounds.minY < visibleTop || bounds.maxY > visibleBottom;

    if (force || needsX) nextX = Math.max(0, bounds.centerX - desiredScreenX);
    if (force || needsY) nextY = Math.max(0, bounds.centerY - desiredScreenY);

    if (Math.abs(nextX - scrollX) > 8 || Math.abs(nextY - scrollY) > 8) {
      window.scrollTo({ left: nextX, top: nextY, behavior: "auto" });
    }
  }

  function xForNode(node, layout) {
    return layout.centers[node.track] + node.sequence * TRACK_OFFSET;
  }

  function layoutNode(node, now, layout) {
    const status = statusFor(node, now);
    const rawY1 = yForTime(node.startMs);
    const rawY2 = yForTime(status === "running" ? now : node.endMs);
    const y1 = status === "running" ? Math.min(rawY1, rawY2 - 28) : rawY1;
    const y2 = Math.max(y1 + 4, rawY2);
    const cx = xForNode(node, layout);
    return {
      x: cx - NODE_WIDTH / 2,
      cx,
      y1,
      y2,
      width: NODE_WIDTH,
      height: Math.max(4, y2 - y1),
      status,
    };
  }

  function directRelationSets(id, now) {
    const ancestors = new Set();
    const descendants = new Set();
    const ancestorEdges = new Set();
    const descendantEdges = new Set();
    const selected = id ? nodeById.get(id) : null;

    if (!selected) return { ancestors, descendants, ancestorEdges, descendantEdges };

    selected.parents.forEach((parentId) => {
      const parent = nodeById.get(parentId);
      if (parent && parent.startMs <= now) {
        ancestors.add(parentId);
        ancestorEdges.add(`${parentId}-${selected.id}`);
      }
    });

    selected.children.forEach((childId) => {
      const child = nodeById.get(childId);
      if (child && child.startMs <= now) {
        descendants.add(childId);
        descendantEdges.add(`${selected.id}-${childId}`);
      }
    });

    return { ancestors, descendants, ancestorEdges, descendantEdges };
  }

  function birthEffectSets() {
    return {
      births: new Set(),
      ancestors: new Set(),
      edges: new Set(),
    };
  }

  function icon(type) {
    const icons = {
      cube: '<path d="M20 4 7 11v18l13 7 13-7V11L20 4Z"/><path d="m7 11 13 8 13-8"/><path d="M20 19v17"/>',
      server: '<rect x="8" y="6" width="24" height="10" rx="2"/><rect x="8" y="24" width="24" height="10" rx="2"/><path d="M14 11h.1M14 29h.1M22 11h6M22 29h6"/>',
      pulse: '<path d="M4 22h7l4-12 7 22 5-14 3 4h6"/>',
      dna: '<path d="M13 5c13 7 13 23 0 30M27 5c-13 7-13 23 0 30"/><path d="M14 10h12M11 18h18M11 26h18M14 34h12"/>',
      trophy: '<path d="M13 8h14v8c0 5-3 9-7 9s-7-4-7-9V8Z"/><path d="M13 11H7c0 5 2 9 7 10M27 11h6c0 5-2 9-7 10"/><path d="M20 25v7M14 34h12"/>',
      target: '<circle cx="20" cy="20" r="12"/><circle cx="20" cy="20" r="5"/><path d="M20 3v5M20 32v5M3 20h5M32 20h5"/>',
      shield: '<path d="M20 4 9 8v9c0 8 5 14 11 18 6-4 11-10 11-18V8L20 4Z"/><path d="M20 10v18M14 17h12"/>',
      group: '<circle cx="14" cy="14" r="4"/><circle cx="26" cy="14" r="4"/><circle cx="20" cy="25" r="4"/><path d="M6 31c1-5 5-8 10-8M34 31c-1-5-5-8-10-8M12 36c1-5 4-7 8-7s7 2 8 7"/>',
      clock: '<circle cx="20" cy="20" r="14"/><path d="M20 11v10l7 4"/>',
      star: '<path d="m20 5 4.3 8.7 9.7 1.4-7 6.8 1.7 9.6L20 27l-8.7 4.5 1.7-9.6-7-6.8 9.7-1.4L20 5Z"/>',
    };
    return `<span class="metric-icon"><svg viewBox="0 0 40 40" aria-hidden="true">${icons[type] || icons.cube}</svg></span>`;
  }

  function renderMetricCard(metric) {
    const cls = ["metric-value", metric.hot ? "hot" : "", metric.small ? "small" : ""]
      .filter(Boolean)
      .join(" ");
    return `
      <article class="metric-card">
        ${icon(metric.icon)}
        <div class="metric-content">
          <p class="metric-cn">${metric.cn}</p>
          <p class="metric-en">${metric.en}</p>
          <p class="${cls}">${metric.value}</p>
        </div>
      </article>
    `;
  }

  function renderDetail(now) {
    if (!detailOpen) {
      detailPanel.classList.remove("open");
      detailPanel.innerHTML = "";
      return;
    }

    detailPanel.classList.add("open");
    const visible = visibleNodes(now);
    const completed = completedNodes(now);
    const running = runningNodes(now);
    const avgParents = visible.length
      ? visible.reduce((sum, node) => sum + node.parents.length, 0) / visible.length
      : 0;

    if (selectedId && nodeById.has(selectedId) && nodeById.get(selectedId).startMs <= now) {
      const node = nodeById.get(selectedId);
      const status = statusFor(node, now);
      const end = status === "running" ? now : node.endMs;
      detailPanel.innerHTML = `
        <div><b>孩子编号 / Child</b><span>#${node.id}</span></div>
        <div><b>设备号 / Device</b><span>${node.track + 1} / ${node.trackLabel}</span></div>
        <div><b>设备序列 / Sequence</b><span>${node.sequence + 1}</span></div>
        <div><b>直接祖先 / Direct Ancestors</b><span>${node.parents.length}</span></div>
        <div><b>直接后代 / Direct Descendants</b><span>${node.children.length}</span></div>
        <div><b>开始 / Started</b><span>${fmtDate(node.startMs)}</span></div>
        <div><b>结束 / Ended</b><span>${status === "running" ? "运行中 / Running" : fmtDate(node.endMs)}</span></div>
        <div><b>已运行 / Elapsed</b><span>${fmtDuration(end - node.startMs)}</span></div>
      `;
      return;
    }

    detailPanel.innerHTML = `
      <div><b>进化开始 / Evolution Start</b><span>${fmtDate(minMs)}</span></div>
      <div><b>当前时间 / Current Time</b><span>${fmtDate(now)}</span></div>
      <div><b>已生成 / Born</b><span>${visible.length}</span></div>
      <div><b>已完成 / Completed</b><span>${completed.length}</span></div>
      <div><b>运行中 / Running</b><span>${running.length}</span></div>
      <div><b>设备状态 / Devices</b><span>${trackRunningSummary(now)}</span></div>
      <div><b>平均祖先 / Avg Ancestors</b><span>${avgParents.toFixed(2)}</span></div>
    `;
  }

  function renderMetrics(now) {
    const visible = visibleNodes(now);
    const running = runningNodes(now);
    const completed = completedNodes(now);
    const avgParents = visible.length
      ? visible.reduce((sum, node) => sum + node.parents.length, 0) / visible.length
      : 0;
    const scored = visible
      .map((node) => scoreFor(node, now))
      .filter((score) => score !== null);

    let metrics;
    if (selectedId && nodeById.has(selectedId) && nodeById.get(selectedId).startMs <= now) {
      const selected = nodeById.get(selectedId);
      const selectedStatus = statusFor(selected, now);
      const end = selectedStatus === "running" ? now : selected.endMs;
      metrics = [
        { icon: "target", cn: "选中孩子", en: "Selected Child", value: `#${selected.id}`, hot: true },
        {
          icon: "server",
          cn: "设备号",
          en: "Device No.",
          value: `${selected.track + 1} / ${selected.trackLabel}`,
          hot: true,
        },
        {
          icon: "cube",
          cn: "设备序列",
          en: "Device Sequence",
          value: String(selected.sequence + 1),
        },
        {
          icon: "shield",
          cn: "祖先",
          en: "ancestors",
          value: selected.parents.length ? selected.parents.map((id) => `#${id}`).join("&nbsp;&nbsp;") : "--",
          small: true,
        },
        {
          icon: "group",
          cn: "后代",
          en: "descendants",
          value: selected.children.length ? selected.children.map((id) => `#${id}`).join("&nbsp;&nbsp;") : "--",
          small: true,
        },
        {
          icon: "clock",
          cn: "存活时间",
          en: "Living Time",
          value: `${fmtDate(selected.startMs)}<br>${fmtDate(end)}<br><span class="metric-value hot small">${fmtDuration(end - selected.startMs)}</span>`,
          small: true,
        },
        {
          icon: "star",
          cn: selectedStatus === "running" ? "当前得分" : "最终得分",
          en: selectedStatus === "running" ? "Current Score" : "Final Score",
          value: `${scoreFor(selected, now).toFixed(2)}/100`,
          hot: true,
        },
      ];
    } else {
      const avgLiving = running.length
        ? running.reduce((sum, node) => sum + now - node.startMs, 0) / running.length
        : 0;
      metrics = [
        {
          icon: "clock",
          cn: "进化开始",
          en: "Evolution Start",
          value: fmtDate(minMs).replace(" ", "<br>"),
          small: true,
        },
        {
          icon: "cube",
          cn: "当前代际",
          en: "Current Generation",
          value: String(Math.max(...visible.map((node) => node.sequence + 1), 0)),
          hot: true,
        },
        { icon: "server", cn: "当前设备数", en: "Device Number", value: String(DATA.tracks.length), hot: true },
        {
          icon: "target",
          cn: "已生成孩子",
          en: "Children Born",
          value: String(visible.length),
          hot: true,
        },
        {
          icon: "group",
          cn: "完成 / 运行",
          en: "Completed / Running",
          value: `${completed.length} / ${running.length}`,
        },
        { icon: "pulse", cn: "平均存活时间", en: "Living Time", value: fmtDuration(avgLiving) },
        {
          icon: "shield",
          cn: "平均祖先",
          en: "Avg Ancestors",
          value: avgParents.toFixed(2),
        },
        { icon: "dna", cn: "进化时间", en: "Evolving Time", value: fmtDuration(now - minMs, true) },
        {
          icon: "trophy",
          cn: "最好成绩",
          en: "Best Score",
          value: `${Math.max(...scored, 0).toFixed(2)}/100`,
        },
      ];
    }

    metricList.innerHTML = metrics.map(renderMetricCard).join("");
  }

  function svgDefs() {
    return `
      <defs>
        <linearGradient id="activeFill" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stop-color="#ff7a12" stop-opacity=".28"/>
          <stop offset="48%" stop-color="#ff9f38" stop-opacity=".62"/>
          <stop offset="100%" stop-color="#ff4f00" stop-opacity=".34"/>
        </linearGradient>
        <linearGradient id="mutedFill" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stop-color="#fff0d0" stop-opacity=".08"/>
          <stop offset="50%" stop-color="#ff9a32" stop-opacity=".22"/>
          <stop offset="100%" stop-color="#ffffff" stop-opacity=".06"/>
        </linearGradient>
        <linearGradient id="ancestorFill" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stop-color="#fff4cb" stop-opacity=".18"/>
          <stop offset="52%" stop-color="#fff0b8" stop-opacity=".72"/>
          <stop offset="100%" stop-color="#fff4cb" stop-opacity=".18"/>
        </linearGradient>
        <linearGradient id="descendantFill" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stop-color="#ff4a00" stop-opacity=".2"/>
          <stop offset="50%" stop-color="#ff3b00" stop-opacity=".7"/>
          <stop offset="100%" stop-color="#ff9560" stop-opacity=".2"/>
        </linearGradient>
        <linearGradient id="edgeBase" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stop-color="#ff6b00" stop-opacity=".72"/>
          <stop offset="58%" stop-color="#9b6b44" stop-opacity=".42"/>
          <stop offset="100%" stop-color="#666b6a" stop-opacity=".22"/>
        </linearGradient>
        <linearGradient id="edgeAncestor" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stop-color="#ff6b00" stop-opacity=".95"/>
          <stop offset="55%" stop-color="#ffd08a" stop-opacity=".78"/>
          <stop offset="100%" stop-color="#777a76" stop-opacity=".32"/>
        </linearGradient>
        <linearGradient id="edgeDescendant" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stop-color="#ff3300" stop-opacity=".95"/>
          <stop offset="55%" stop-color="#b46a3b" stop-opacity=".62"/>
          <stop offset="100%" stop-color="#656968" stop-opacity=".26"/>
        </linearGradient>
        <linearGradient id="edgeActive" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stop-color="#ff6b00" stop-opacity=".72"/>
          <stop offset="50%" stop-color="#ffd18b" stop-opacity=".9"/>
          <stop offset="100%" stop-color="#ff8a14" stop-opacity=".62"/>
        </linearGradient>
        <filter id="nodeGlow" x="-70%" y="-25%" width="240%" height="150%">
          <feGaussianBlur stdDeviation="1.6" result="blur"/>
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        <filter id="lineGlow" x="-35%" y="-35%" width="170%" height="170%">
          <feGaussianBlur stdDeviation="1.2" result="blur"/>
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
    `;
  }

  function capsulePath(x, y1, width, y2, bottomRounded) {
    const r = Math.min(width / 2, Math.max(2, (y2 - y1) / 2));
    const bottomR = bottomRounded ? r : 0;
    const right = x + width;
    const top = y1;
    const bottom = y2;

    if (bottomRounded) {
      return [
        `M ${x + r} ${top}`,
        `C ${x + width * 0.16} ${top}, ${x} ${top + r * 0.18}, ${x} ${top + r}`,
        `L ${x} ${bottom - bottomR}`,
        `C ${x} ${bottom - bottomR * 0.16}, ${x + bottomR * 0.16} ${bottom}, ${x + bottomR} ${bottom}`,
        `L ${right - bottomR} ${bottom}`,
        `C ${right - bottomR * 0.16} ${bottom}, ${right} ${bottom - bottomR * 0.16}, ${right} ${bottom - bottomR}`,
        `L ${right} ${top + r}`,
        `C ${right} ${top + r * 0.18}, ${right - width * 0.16} ${top}, ${x + r} ${top}`,
        "Z",
      ].join(" ");
    }

    return [
      `M ${x + r} ${top}`,
      `C ${x + width * 0.16} ${top}, ${x} ${top + r * 0.18}, ${x} ${top + r}`,
      `L ${x} ${bottom}`,
      `L ${right} ${bottom}`,
      `L ${right} ${top + r}`,
      `C ${right} ${top + r * 0.18}, ${right - width * 0.16} ${top}, ${x + r} ${top}`,
      "Z",
    ].join(" ");
  }

  function edgeCurve(edge, positions) {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    if (!source || !target) return null;
    const sourceLeft = target.cx < source.cx;
    const sx = sourceLeft ? source.x : source.x + source.width;
    const sy = source.y2 - Math.min(26, source.height * 0.25);
    const tx = target.cx;
    const ty = target.y1 + 2;
    const dx = tx - sx;
    const dy = Math.max(24, ty - sy);
    return {
      sx,
      sy,
      c1x: sx + dx * 0.38,
      c1y: sy + dy * 0.18,
      c2x: tx - dx * 0.22,
      c2y: ty - Math.min(92, dy * 0.48),
      tx,
      ty,
    };
  }

  function edgePathFromCurve(curve) {
    return `M ${curve.sx.toFixed(2)} ${curve.sy.toFixed(2)} C ${curve.c1x.toFixed(2)} ${curve.c1y.toFixed(2)}, ${curve.c2x.toFixed(2)} ${curve.c2y.toFixed(2)}, ${curve.tx.toFixed(2)} ${curve.ty.toFixed(2)}`;
  }

  function ribbonPath(curve, startWidth, endWidth) {
    const s = startWidth / 2;
    const e = endWidth / 2;
    return [
      `M ${curve.sx.toFixed(2)} ${(curve.sy - s).toFixed(2)}`,
      `C ${curve.c1x.toFixed(2)} ${(curve.c1y - s).toFixed(2)}, ${curve.c2x.toFixed(2)} ${(curve.c2y - e).toFixed(2)}, ${curve.tx.toFixed(2)} ${(curve.ty - e).toFixed(2)}`,
      `L ${curve.tx.toFixed(2)} ${(curve.ty + e).toFixed(2)}`,
      `C ${curve.c2x.toFixed(2)} ${(curve.c2y + e).toFixed(2)}, ${curve.c1x.toFixed(2)} ${(curve.c1y + s).toFixed(2)}, ${curve.sx.toFixed(2)} ${(curve.sy + s).toFixed(2)}`,
      "Z",
    ].join(" ");
  }

  function renderEdge(edge, positions, relation, selected) {
    const curve = edgeCurve(edge, positions);
    if (!curve) return "";
    const center = edgePathFromCurve(curve);
    if (relation === "birth") {
      return `
        <path d="${ribbonPath(curve, 12, 2.4)}" fill="url(#edgeDescendant)" opacity=".78"/>
        <path d="${center}" pathLength="1" fill="none" stroke="#ffd18b" stroke-width="3.2" stroke-linecap="round"/>
      `;
    }
    if (relation === "ancestor") {
      return `<path d="${ribbonPath(curve, 11, 2.2)}" fill="url(#edgeAncestor)" opacity=".92"/><path d="${center}" fill="none" stroke="var(--tree-edge-highlight)" stroke-width="1.3" stroke-linecap="round"/>`;
    }
    if (relation === "descendant") {
      return `<path d="${ribbonPath(curve, 10, 1.8)}" fill="url(#edgeDescendant)" opacity=".9"/><path d="${center}" fill="none" stroke="rgba(255,80,18,.64)" stroke-width="1.15" stroke-linecap="round"/>`;
    }
    if (relation === "active") {
      return `<path d="${ribbonPath(curve, 10.5, 2.1)}" fill="url(#edgeActive)" opacity=".88"/><path d="${center}" fill="none" stroke="#ffd18b" stroke-width="1.45" stroke-linecap="round" filter="url(#lineGlow)"/>`;
    }
    return `<path d="${ribbonPath(curve, 7.2, 1.2)}" fill="url(#edgeBase)" opacity="${selected ? 0.08 : 0.34}"/><path d="${center}" fill="none" stroke="rgba(112,116,113,${selected ? 0.08 : 0.24})" stroke-width=".9" stroke-linecap="round"/>`;
  }

  function renderNode(node, now, pos, relationState) {
    const selected = selectedId === node.id;
    const running = pos.status === "running";
    const born = relationState === "birth";
    const birthAncestor = relationState === "birthAncestor";
    const related = relationState === "ancestor" || relationState === "descendant" || born || birthAncestor;
    const muted = selectedId && !selected && !related;
    const fill = muted
      ? "url(#mutedFill)"
      : born || selected || running
        ? "url(#activeFill)"
        : relationState === "ancestor" || birthAncestor
          ? "url(#ancestorFill)"
          : relationState === "descendant"
            ? "url(#descendantFill)"
            : "url(#mutedFill)";
    const stroke = muted
      ? "rgba(176,184,178,.48)"
      : born || selected || running
        ? "#ffd08a"
        : relationState === "ancestor" || birthAncestor
          ? "#fff3c2"
          : relationState === "descendant"
            ? "#ff3a00"
            : "rgba(255,180,92,.42)";
    const opacity = muted ? 0.34 : selected || related ? 0.98 : running ? 0.82 : 0.5;
    const bottomRounded = !running;
    const d = capsulePath(pos.x, pos.y1, pos.width, pos.y2, bottomRounded);
    const innerD =
      pos.height > 18
        ? capsulePath(
            pos.x + 6,
            pos.y1 + 7,
            pos.width - 12,
            Math.max(pos.y1 + 10, pos.y2 - (bottomRounded ? 7 : 0)),
            bottomRounded,
          )
        : "";
    const ribCount = Math.min(8, Math.max(1, Math.floor(pos.height / 34)));
    const ribs = Array.from({ length: ribCount }, (_, index) => {
      const y = pos.y1 + 15 + index * ((pos.height - 28) / Math.max(1, ribCount - 1));
      if (y >= pos.y2 - 4) return "";
      return `<line x1="${(pos.x + 7).toFixed(1)}" y1="${y.toFixed(1)}" x2="${(pos.x + pos.width - 7).toFixed(1)}" y2="${y.toFixed(1)}" stroke="rgba(255,235,205,.12)" stroke-width=".65"/>`;
    }).join("");

    return `
      <g class="node-hit ${selected ? "is-selected" : ""}" data-node-id="${node.id}" opacity="${opacity.toFixed(2)}">
        <path d="${d}" fill="${fill}" stroke="${stroke}" stroke-width="${born || selected ? 2.4 : 1.25}" ${selected || related ? 'filter="url(#nodeGlow)"' : ""}/>
        ${innerD ? `<path d="${innerD}" fill="rgba(255,244,219,.055)"/>` : ""}
        ${pos.height > 16 ? `<line x1="${(pos.x + pos.width * 0.68).toFixed(1)}" y1="${(pos.y1 + 8).toFixed(1)}" x2="${(pos.x + pos.width * 0.68).toFixed(1)}" y2="${(pos.y2 - 5).toFixed(1)}" stroke="rgba(255,255,255,.11)" stroke-width=".8"/>` : ""}
        ${ribs}
        <rect x="${(pos.x - 13).toFixed(1)}" y="${(pos.y1 - 8).toFixed(1)}" width="${pos.width + 26}" height="${Math.max(18, pos.y2 - pos.y1 + 16).toFixed(1)}" fill="transparent">
          <title>#${node.id}</title>
        </rect>
      </g>
    `;
  }

  function renderRails(layout, canvas, now) {
    const labels = DATA.tracks
      .map((label, track) => {
        const x1 = layout.centers[track];
        const x2 = x1 + canvas.maxSequence * TRACK_OFFSET;
        return `
          <g class="track-rail">
            <path d="M ${x1.toFixed(1)} ${TOP_PAD - 34} L ${x2.toFixed(1)} ${(canvas.currentY + 34).toFixed(1)}" stroke="var(--tree-rail)" stroke-width="1.1" stroke-dasharray="8 15"/>
            <text x="${x1.toFixed(1)}" y="${TOP_PAD - 47}" fill="var(--tree-muted-text)" font-size="14" text-anchor="middle">设备 ${track + 1} / ${label}</text>
          </g>
        `;
      })
      .join("");
    return `<g>${labels}</g>`;
  }

  function renderCurrentLine(canvas) {
    const y = canvas.currentY;
    const x2 = canvas.stageWidth - 82;
    return `
      <g class="current-time">
        <line x1="48" y1="${y.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y.toFixed(1)}" stroke="var(--tree-current)" stroke-width="1.5" stroke-dasharray="10 9" opacity=".92"/>
        <text x="54" y="${(y - 10).toFixed(1)}" fill="var(--tree-text)" font-size="13">当前时间 / Current Time</text>
      </g>
    `;
  }

  function renderTimeline(canvas) {
    const x = canvas.stageWidth - 82;
    const top = TOP_PAD - 34;
    const bottom = canvas.currentY;
    return `
      <g class="timeline-layer">
        <path d="M ${x} ${top} L ${x} ${bottom}" stroke="var(--tree-rail)" stroke-width="4.4" stroke-linecap="round"/>
        <path d="M ${x} ${top} L ${x} ${bottom}" stroke="#ff8a14" stroke-width="2.1" stroke-linecap="round" filter="url(#lineGlow)"/>
        <path d="M ${x - 12} ${bottom - 13} L ${x} ${bottom + 10} L ${x + 12} ${bottom - 13} Z" fill="rgba(255,130,20,.18)" stroke="#ffd18b" stroke-width="2.2" stroke-linejoin="round" filter="url(#nodeGlow)"/>
        <circle cx="${x}" cy="${bottom}" r="4.2" fill="var(--tree-current)" opacity=".86"/>
        <text x="${x + 46}" y="${(bottom - 35).toFixed(1)}" fill="var(--tree-text)" font-size="17" text-anchor="middle">时间线</text>
        <text x="${x + 46}" y="${(bottom - 11).toFixed(1)}" fill="var(--tree-muted-text)" font-size="15" text-anchor="middle">timeline</text>
      </g>
    `;
  }

  function renderTree(now, canvas) {
    treeSvg.setAttribute("viewBox", `0 0 ${canvas.stageWidth} ${canvas.height}`);
    treeSvg.setAttribute("preserveAspectRatio", "xMinYMin meet");

    const layout = trackLayout(canvas.stageWidth, canvas.maxSequence);
    const visible = visibleNodes(now);
    const visibleIds = new Set(visible.map((node) => node.id));
    const relations = directRelationSets(selectedId, now);
    const birthEffects = birthEffectSets();
    const positions = new Map(
      visible.map((node) => [node.id, layoutNode(node, now, layout)]),
    );
    const runningIds = playbackMode
      ? new Set(visible.filter((node) => statusFor(node, now) === "running").map((node) => node.id))
      : new Set();
    const activeEdgeIds = new Set(
      edges
        .filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))
        .filter((edge) => runningIds.has(edge.source) || runningIds.has(edge.target))
        .map((edge) => edge.id),
    );

    const edgeMarkup = edges
      .filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))
      .filter(
        (edge) =>
          !selectedId ||
          relations.ancestorEdges.has(edge.id) ||
          relations.descendantEdges.has(edge.id) ||
          activeEdgeIds.has(edge.id) ||
          birthEffects.edges.has(edge.id),
      )
      .map((edge) => {
        let relation = "base";
        if (relations.ancestorEdges.has(edge.id)) relation = "ancestor";
        if (relations.descendantEdges.has(edge.id)) relation = "descendant";
        if (activeEdgeIds.has(edge.id)) relation = "active";
        if (birthEffects.edges.has(edge.id)) relation = "birth";
        return renderEdge(edge, positions, relation, Boolean(selectedId));
      })
      .join("");

    const nodeMarkup = visible
      .map((node) => {
        let relationState = "base";
        if (relations.ancestors.has(node.id)) relationState = "ancestor";
        if (relations.descendants.has(node.id)) relationState = "descendant";
        if (birthEffects.ancestors.has(node.id)) relationState = "birthAncestor";
        if (birthEffects.births.has(node.id)) relationState = "birth";
        return renderNode(node, now, positions.get(node.id), relationState);
      })
      .join("");

    treeSvg.innerHTML = `
      ${svgDefs()}
      <rect x="0" y="0" width="${canvas.stageWidth}" height="${canvas.height}" fill="transparent"/>
      ${renderRails(layout, canvas, now)}
      <g class="edge-layer">${edgeMarkup}</g>
      <g class="node-layer">${nodeMarkup}</g>
      ${renderCurrentLine(canvas)}
      ${renderTimeline(canvas)}
    `;
  }

  function chartPath(points) {
    if (!points.length) return "";
    let d = `M ${points[0].x} ${points[0].y}`;
    for (let index = 1; index < points.length; index += 1) {
      const previous = points[index - 1];
      const current = points[index];
      const midX = (previous.x + current.x) / 2;
      d += ` C ${midX.toFixed(1)} ${previous.y.toFixed(1)}, ${midX.toFixed(1)} ${current.y.toFixed(1)}, ${current.x.toFixed(1)} ${current.y.toFixed(1)}`;
    }
    return d;
  }

  function renderTrend(now) {
    const width = Math.max(420, Math.round(trendSvg.getBoundingClientRect().width || 680));
    const height = Math.max(244, Math.round(trendSvg.getBoundingClientRect().height || 396));
    trendSvg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    trendSvg.setAttribute("preserveAspectRatio", "xMinYMin meet");

    const visible = visibleNodes(now)
      .map((node) => ({ node, score: scoreFor(node, now) }))
      .filter((item) => item.score !== null)
      .sort((a, b) => a.node.startMs - b.node.startMs);
    const chart = { left: 70, top: 68, right: width - 42, bottom: height - 76 };
    const scores = visible.map((item) => item.score);
    const minScore = Math.floor(Math.min(...scores, 35) / 5) * 5;
    const maxScore = Math.ceil(Math.max(...scores, 80) / 5) * 5;
    const xGridSteps = width < 560 ? 4 : 6;
    const yGridSteps = 4;
    const timeSpan = Math.max(1, now - minMs);
    const xScale = fmtScaleDuration(timeSpan / xGridSteps);
    const yScale = ((maxScore - minScore) / yGridSteps).toFixed(1).replace(/\.0$/, "");
    const xFor = (node) => chart.left + ((node.startMs - minMs) / (now - minMs || 1)) * (chart.right - chart.left);
    const yFor = (score) => chart.bottom - ((score - minScore) / (maxScore - minScore || 1)) * (chart.bottom - chart.top);
    const points = visible.map((item) => ({
      id: item.node.id,
      node: item.node,
      score: item.score,
      x: clamp(xFor(item.node), chart.left, chart.right),
      y: clamp(yFor(item.score), chart.top, chart.bottom),
    }));
    const path = chartPath(points);
    const area = points.length
      ? `${path} L ${points[points.length - 1].x.toFixed(1)} ${chart.bottom} L ${points[0].x.toFixed(1)} ${chart.bottom} Z`
      : "";
    const selected = selectedId ? points.find((point) => point.id === selectedId) : null;

    trendSvg.innerHTML = `
      <defs>
        <linearGradient id="chartLine" x1="${chart.left}" y1="0" x2="${chart.right}" y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#ff4f00"/>
          <stop offset="48%" stop-color="#ffd18b"/>
          <stop offset="100%" stop-color="#ff7a00"/>
        </linearGradient>
        <linearGradient id="chartArea" x1="0" y1="${chart.top}" x2="0" y2="${chart.bottom}" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="rgba(255,145,31,.34)"/>
          <stop offset="100%" stop-color="rgba(255,145,31,0)"/>
        </linearGradient>
        <filter id="chartGlow" x="-70%" y="-70%" width="240%" height="240%">
          <feGaussianBlur stdDeviation="1.8" result="blur"/>
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      <text x="${chart.left}" y="30" fill="var(--tree-text)" font-size="20" font-weight="700">总体趋势 / Overall Trend</text>
      <text x="${chart.left}" y="49" fill="var(--tree-muted-text)" font-size="12">由孩子节点实时生成 / generated from visible child nodes</text>
      <g opacity=".22">
        ${Array.from({ length: yGridSteps + 1 }, (_, index) => {
          const y = chart.top + index * ((chart.bottom - chart.top) / yGridSteps);
          return `<line x1="${chart.left}" y1="${y.toFixed(1)}" x2="${chart.right}" y2="${y.toFixed(1)}" stroke="var(--tree-rail)" stroke-width="1"/>`;
        }).join("")}
        ${Array.from({ length: xGridSteps + 1 }, (_, index) => {
          const x = chart.left + index * ((chart.right - chart.left) / xGridSteps);
          return `<line x1="${x.toFixed(1)}" y1="${chart.top}" x2="${x.toFixed(1)}" y2="${chart.bottom}" stroke="var(--tree-rail)" stroke-width="1"/>`;
        }).join("")}
      </g>
      <g class="axis-labels" fill="var(--tree-soft-text)" font-size="10">
        ${Array.from({ length: yGridSteps + 1 }, (_, index) => {
          const y = chart.top + index * ((chart.bottom - chart.top) / yGridSteps);
          const value = maxScore - index * ((maxScore - minScore) / yGridSteps);
          return `
            <line x1="${chart.left - 5}" y1="${y.toFixed(1)}" x2="${chart.left}" y2="${y.toFixed(1)}" stroke="var(--tree-soft-text)" stroke-width="1"/>
            <text x="${chart.left - 10}" y="${(y + 3.5).toFixed(1)}" text-anchor="end">${value.toFixed(0)}</text>
          `;
        }).join("")}
        ${Array.from({ length: xGridSteps + 1 }, (_, index) => {
          const x = chart.left + index * ((chart.right - chart.left) / xGridSteps);
          const tick = fmtAxisDate(minMs + (timeSpan * index) / xGridSteps);
          const anchor = index === 0 ? "start" : index === xGridSteps ? "end" : "middle";
          return `
            <line x1="${x.toFixed(1)}" y1="${chart.bottom}" x2="${x.toFixed(1)}" y2="${chart.bottom + 5}" stroke="var(--tree-soft-text)" stroke-width="1"/>
            <text x="${x.toFixed(1)}" y="${chart.bottom + 18}" text-anchor="${anchor}">
              <tspan x="${x.toFixed(1)}">${tick.date}</tspan>
              <tspan x="${x.toFixed(1)}" dy="12">${tick.time}</tspan>
            </text>
          `;
        }).join("")}
      </g>
      <path d="M ${chart.left} ${chart.bottom} V ${chart.top - 2}" stroke="var(--tree-axis)" stroke-width="2.4" stroke-linecap="round"/>
      <path d="M ${chart.left - 9} ${chart.top + 10} L ${chart.left} ${chart.top - 4} L ${chart.left + 9} ${chart.top + 10}" fill="none" stroke="var(--tree-axis)" stroke-width="2.4" stroke-linecap="round"/>
      <path d="M ${chart.left} ${chart.bottom} H ${chart.right}" stroke="var(--tree-axis)" stroke-width="2.4" stroke-linecap="round"/>
      <path d="M ${chart.right - 11} ${chart.bottom - 9} L ${chart.right + 4} ${chart.bottom} L ${chart.right - 11} ${chart.bottom + 9}" fill="none" stroke="var(--tree-axis)" stroke-width="2.4" stroke-linecap="round"/>
      <text x="${(chart.left + chart.right) / 2}" y="${height - 12}" fill="var(--tree-soft-text)" font-size="11" text-anchor="middle">横轴：时间 / Time (Asia/Shanghai) · 1格=${xScale}</text>
      <text x="15" y="${(chart.top + chart.bottom) / 2}" fill="var(--tree-soft-text)" font-size="11" text-anchor="middle" transform="rotate(-90 15 ${(chart.top + chart.bottom) / 2})">纵轴：得分 / Score (/100) · 1格=${yScale}分</text>
      ${selected ? `<line x1="${selected.x.toFixed(1)}" y1="${chart.top}" x2="${selected.x.toFixed(1)}" y2="${chart.bottom}" stroke="var(--tree-current)" stroke-width="1.5" stroke-dasharray="6 7"/>` : ""}
      ${area ? `<path d="${area}" fill="url(#chartArea)"/>` : ""}
      <path d="${path}" fill="none" stroke="rgba(255,100,0,.25)" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" filter="url(#chartGlow)"/>
      <path d="${path}" fill="none" stroke="url(#chartLine)" stroke-width="4.4" stroke-linecap="round" stroke-linejoin="round"/>
      ${points
        .map((point) => {
          const active = statusFor(point.node, now) === "running";
          const picked = point.id === selectedId;
          const radius = picked ? 8.5 : active ? 5.6 : 3.2;
          return `<circle class="trend-point" data-node-id="${point.id}" cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="${radius}" fill="${picked ? "#fff8db" : active ? "#ff8a14" : "#d79745"}" stroke="${picked ? "#ff3000" : "rgba(255,235,198,.58)"}" stroke-width="${picked ? 3.2 : 1.2}" ${picked || active ? 'filter="url(#chartGlow)"' : ""}/>`;
        })
        .join("")}
    `;
  }

  function renderPlayback(now) {
    const progress = clamp((now - minMs) / (maxMs - minMs), 0, 1);
    playbackSlider.value = String(Math.round(progress * 10000));
    playbackTime.innerHTML = `${fmtDate(now)}<br>${playbackMode ? "播放中 / Playing" : manualMode ? "手动定位 / Manual" : "实时 / Live"}`;
    playToggle.textContent = playbackMode ? "暂停 / Pause" : "播放 / Play";
    speedSelect.value = String(playbackSpeed);
  }

  function renderAll(force = false) {
    const now = currentMs();
    const tick = playbackMode ? Math.floor(Date.now() / PLAYBACK_FRAME_MS) : Math.floor(now / 1000);
    if (!force && tick === lastRenderedSecond) return;
    lastRenderedSecond = tick;

    if (selectedId) {
      const selected = nodeById.get(selectedId);
      if (!selected || selected.startMs > now) selectedId = null;
    }

    const canvas = updateCanvas(now);
    renderMetrics(now);
    renderDetail(now);
    renderTree(now, canvas);
    renderTrend(now);
    renderPlayback(now);
    ensureCurrentCapsulesVisible(now, canvas, force);
    timeReadout.innerHTML = `${fmtDate(now)}<br>当前时间 / Current Time`;
    if (secretTime) secretTime.textContent = fmtDate(now);

    if (!manualMode && timeSlider) {
      timeSlider.value = String(Math.round(((now - minMs) / (maxMs - minMs)) * 10000));
    }

    if (playbackMode && now >= maxMs) {
      playbackMode = false;
      manualMode = true;
      manualMs = maxMs;
      renderPlayback(maxMs);
    }
  }

  function selectNode(id) {
    const now = currentMs();
    const node = nodeById.get(id);
    if (!node || node.startMs > now) return;
    selectedId = selectedId === id ? null : id;
    renderAll(true);
  }

  function showTooltip(event, id) {
    const now = currentMs();
    const node = nodeById.get(id);
    if (!node) return;
    const score = scoreFor(node, now);
    const status = statusFor(node, now);
    const end = status === "running" ? now : node.endMs;
    tooltip.innerHTML = `
      <strong>#${node.id}</strong>
      <p>设备 / Device ${node.track + 1}</p>
      <p>状态 / Status ${status === "running" ? "running" : "completed"}</p>
      <p>得分 / Score ${score === null ? "--" : score.toFixed(2)}</p>
      <p>时长 / Duration ${fmtDuration(end - node.startMs)}</p>
    `;
    tooltip.style.transform = `translate(${event.clientX + 16}px, ${event.clientY + 16}px)`;
    tooltip.classList.add("visible");
  }

  function hideTooltip() {
    tooltip.classList.remove("visible");
    tooltip.style.transform = "translate(-999px, -999px)";
  }

  function handleClick(event) {
    const target = event.target.closest("[data-node-id]");
    if (target) {
      selectNode(target.getAttribute("data-node-id"));
    } else if (event.currentTarget === treeSvg) {
      selectedId = null;
      renderAll(true);
    }
  }

  function handleMove(event) {
    const target = event.target.closest("[data-node-id]");
    if (!target) {
      hideTooltip();
      return;
    }
    showTooltip(event, target.getAttribute("data-node-id"));
  }

  function setManual(value) {
    manualMs = Math.round(minMs + (Number(value) / 10000) * (maxMs - minMs));
    manualMode = true;
    playbackMode = false;
    if (secretPanel) secretPanel.classList.add("active");
    renderAll(true);
  }

  function setPlaybackPosition(value) {
    const nextMs = Math.round(minMs + (Number(value) / 10000) * (maxMs - minMs));
    manualMode = true;
    playbackMode = false;
    manualMs = nextMs;
    playbackBaseMs = nextMs;
    renderAll(true);
  }

  function returnToLive() {
    manualMode = false;
    playbackMode = false;
    liveBaseMs = clamp(Date.now(), minMs, maxMs);
    liveStartedAt = Date.now();
    selectedId = null;
    if (secretPanel) secretPanel.classList.remove("active");
    lastRenderedSecond = -1;
  }

  function startPlayback(fromStart = false) {
    const now = currentMs();
    playbackMode = true;
    manualMode = false;
    playbackBaseMs = fromStart ? minMs : clamp(now, minMs, maxMs);
    if (playbackBaseMs >= maxMs) playbackBaseMs = minMs;
    playbackStartedAt = Date.now();
    lastRenderedSecond = -1;
    renderAll(true);
  }

  function pausePlayback() {
    returnToLive();
    renderAll(true);
  }

  treeSvg.addEventListener("click", handleClick);
  trendSvg.addEventListener("click", handleClick);
  treeSvg.addEventListener("mousemove", handleMove);
  trendSvg.addEventListener("mousemove", handleMove);
  treeSvg.addEventListener("mouseleave", hideTooltip);
  trendSvg.addEventListener("mouseleave", hideTooltip);
  if (timeSlider) timeSlider.addEventListener("input", (event) => setManual(event.target.value));
  playbackSlider.addEventListener("input", (event) => setPlaybackPosition(event.target.value));
  playToggle.addEventListener("click", () => {
    if (playbackMode) {
      pausePlayback();
    } else {
      startPlayback(false);
    }
  });
  restartPlayback.addEventListener("click", () => startPlayback(true));
  speedSelect.addEventListener("change", (event) => {
    const now = currentMs();
    playbackSpeed = Number(event.target.value);
    if (playbackMode) {
      playbackBaseMs = now;
      playbackStartedAt = Date.now();
    }
    renderPlayback(now);
  });
  detailButton.addEventListener("click", () => {
    window.location.href = "./Child-流程图/index.html";
  });
  if (liveButton) {
    liveButton.addEventListener("click", () => {
      returnToLive();
      renderAll(true);
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key.toLowerCase() === "t" && event.shiftKey && secretPanel) secretPanel.classList.toggle("active");
    if (event.key === "Escape") {
      selectedId = null;
      renderAll(true);
    }
  });
  window.addEventListener("resize", () => renderAll(true));
  window.addEventListener("child-theme-change", () => renderAll(true));

  renderAll(true);
  function animationLoop(timestamp) {
    const minFrameGap = playbackMode ? PLAYBACK_FRAME_MS : IDLE_FRAME_MS;

    if (!lastFrameAt || timestamp - lastFrameAt >= minFrameGap) {
      renderAll(false);
      lastFrameAt = timestamp;
    }

    window.requestAnimationFrame(animationLoop);
  }

  window.requestAnimationFrame(animationLoop);
})();

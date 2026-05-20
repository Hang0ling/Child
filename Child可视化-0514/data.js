(function () {
  const hourMs = 60 * 60 * 1000;
  const minuteMs = 60 * 1000;
  const minMs = Date.parse("2026-05-05T08:00:00+08:00");
  const maxMs = Date.parse("2026-05-16T23:59:00+08:00");
  const trackLabels = ["Alpha", "Beta", "Gamma"];
  const baseDurations = [210, 285, 365];
  const durationSteps = [34, 42, 52];

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function isoShanghai(ms) {
    const date = new Date(ms + 8 * hourMs);
    return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}T${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())}+08:00`;
  }

  function gapMinutesFor(track, sequence) {
    const noise = Math.sin((track + 1) * 92821 + (sequence + 1) * 68917) * 10000;
    return 5 + Math.floor((noise - Math.floor(noise)) * 4);
  }

  const rawNodes = [];

  trackLabels.forEach((trackLabel, track) => {
    let cursor = minMs;
    let sequence = 0;

    while (cursor < maxMs) {
      const wave = ((sequence + track) % 4) * 14;
      let durationMinutes =
        baseDurations[track] +
        sequence * durationSteps[track] +
        Math.floor(sequence / 3) * 28 +
        wave;

      if ((sequence === 4 && track === 1) || (sequence === 7 && track === 0) || (sequence === 5 && track === 2)) {
        durationMinutes = 72 + track * 18 + sequence * 4;
      } else if ((sequence + track) % 6 === 0 && sequence > 2) {
        durationMinutes = Math.round(durationMinutes * 0.58);
      } else if ((sequence * 2 + track) % 7 === 3) {
        durationMinutes = Math.round(durationMinutes * 1.34);
      }

      durationMinutes = Math.max(58, durationMinutes);
      const startMs = cursor;
      const endMs = Math.min(maxMs + 2 * hourMs, startMs + durationMinutes * minuteMs);

      rawNodes.push({
        track,
        trackLabel,
        sequence,
        generation: sequence + 1,
        startMs,
        endMs,
        durationMinutes,
        startedAt: isoShanghai(startMs),
        endedAt: isoShanghai(endMs),
      });

      cursor = endMs + gapMinutesFor(track, sequence) * minuteMs;
      sequence += 1;
    }
  });

  rawNodes.sort((a, b) => a.startMs - b.startMs || a.track - b.track);

  const nodes = rawNodes.map((node, index) => {
    const score = Math.min(
      92,
      39 + index * 0.92 + node.sequence * 0.82 + node.track * 1.4 + Math.sin(index * 1.17) * 4.7,
    );

    return {
      ...node,
      index,
      id: String(index + 1).padStart(3, "0"),
      label: `#${String(index + 1).padStart(3, "0")}`,
      score: Number(score.toFixed(2)),
      startScore: Number(Math.max(18, score - 9.2 + Math.sin(index * 0.8) * 1.9).toFixed(2)),
      parents: [],
    };
  });

  const nodesByTrack = trackLabels.map((_, track) =>
    nodes.filter((node) => node.track === track).sort((a, b) => a.sequence - b.sequence),
  );

  nodes.forEach((node) => {
    const parents = [];
    const targetParentCount = node.sequence > 2 && node.index % 3 === 0 ? 5 : 4;
    const sameTrackPrevious = nodesByTrack[node.track][node.sequence - 1];
    const candidates = nodes
      .filter((candidate) => candidate.endMs <= node.startMs && candidate.id !== node.id)
      .sort((a, b) => b.endMs - a.endMs || a.track - b.track);

    if (sameTrackPrevious) parents.push(sameTrackPrevious.id);

    candidates
      .filter((candidate) => candidate.track !== node.track)
      .forEach((candidate) => {
        if (parents.length < targetParentCount && !parents.includes(candidate.id)) parents.push(candidate.id);
      });

    candidates.forEach((candidate) => {
      if (parents.length < targetParentCount && !parents.includes(candidate.id)) parents.push(candidate.id);
    });

    node.parents = parents;
  });

  const byId = new Map(nodes.map((node) => [node.id, node]));

  nodes.forEach((node) => {
    node.children = nodes
      .filter((candidate) => candidate.parents.includes(node.id))
      .map((candidate) => candidate.id);
  });

  const edges = nodes.flatMap((node) =>
    node.parents.map((parentId) => ({
      id: `${parentId}-${node.id}`,
      source: parentId,
      target: node.id,
    })),
  );

  window.EVOLUTION_DATA = {
    startedAt: isoShanghai(minMs),
    endsAt: isoShanghai(maxMs),
    defaultNow: "2026-05-14T16:02:00+08:00",
    tracks: trackLabels,
    nodes,
    edges,
    meta: {
      averageParentCount:
        nodes.reduce((sum, node) => sum + node.parents.length, 0) / Math.max(1, nodes.length),
      nodeCountByTrack: nodesByTrack.map((trackNodes) => trackNodes.length),
    },
  };
})();

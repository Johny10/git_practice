(async function () {
  const SOURCE_URLS = {
    geometry:
      "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/secteurs-des-bureaux-de-vote-2026/exports/geojson?limit=-1",
    round1Page: "https://www.paris.fr/elections/municipales-2026-premier-tour",
    round2Page: "https://www.paris.fr/elections/municipales-2026-second-tour",
    round1Json:
      "https://cdn.paris.fr/paris/2026/03/18/dc6eb426c9a69721c40d845492d6046c.json",
    round2Json:
      "https://cdn.paris.fr/paris/2026/03/23/1c44370057138acd63333e945033e3a3.json",
  };

  const ROUND_OPTIONS = [
    { id: "round1", label: "First round", short: "15 Mar 2026" },
    { id: "round2", label: "Second round", short: "22 Mar 2026" },
  ];

  const METRIC_OPTIONS = [
    { id: "leader", label: "Leader" },
    { id: "turnout", label: "Turnout" },
    { id: "share", label: "Vote share" },
  ];

  const dom = {
    heroMeta: document.getElementById("hero-meta"),
    heroCards: document.getElementById("hero-cards"),
    roundToggle: document.getElementById("round-toggle"),
    metricToggle: document.getElementById("metric-toggle"),
    candidateGroup: document.getElementById("candidate-group"),
    candidateSelect: document.getElementById("candidate-select"),
    mapTitle: document.getElementById("map-title"),
    legend: document.getElementById("legend"),
    summaryCard: document.getElementById("summary-card"),
    detailCard: document.getElementById("detail-card"),
    sourceCard: document.getElementById("source-card"),
    resetView: document.getElementById("reset-view"),
  };

  function renderLoading() {
    dom.heroMeta.innerHTML = '<span class="meta-pill">Loading official Paris data…</span>';
    dom.heroCards.innerHTML = `
      <article class="stats-card"><div class="stats-label">Status</div><div class="stats-value">Loading</div><div class="stats-subtext">Fetching 2026 bureau geometry and official round feeds.</div></article>
      <article class="stats-card"><div class="stats-label">Source</div><div class="stats-value">Ville de Paris</div><div class="stats-subtext">No local build step, data comes straight from the official endpoints.</div></article>
    `;
    dom.summaryCard.innerHTML = '<div class="detail-title">Loading</div><p class="empty-copy">Preparing the bureau-level map…</p>';
    dom.detailCard.innerHTML = '<div class="detail-title">Loading</div><p class="empty-copy">Fetching first round, second round, and turnout data.</p>';
    dom.sourceCard.innerHTML = '<div class="detail-title">Sources</div><p class="source-copy">Connecting to Ville de Paris official data feeds.</p>';
  }

  function renderError(message) {
    dom.heroMeta.innerHTML = '<span class="meta-pill">Load error</span>';
    dom.heroCards.innerHTML = `
      <article class="stats-card">
        <div class="stats-label">Couldn’t load live data</div>
        <div class="stats-value">Check network</div>
        <div class="stats-subtext">${message}</div>
      </article>
    `;
    dom.summaryCard.innerHTML = '<div class="detail-title">Load error</div><p class="empty-copy">The app could not fetch the official Paris sources from this browser session.</p>';
    dom.detailCard.innerHTML = `<div class="detail-title">Details</div><p class="empty-copy">${message}</p>`;
    dom.sourceCard.innerHTML = `
      <div class="detail-title">Sources</div>
      <p class="source-copy"><a href="${SOURCE_URLS.round1Page}" target="_blank" rel="noreferrer">First round page</a></p>
      <p class="source-copy"><a href="${SOURCE_URLS.round2Page}" target="_blank" rel="noreferrer">Second round page</a></p>
      <p class="source-copy"><a href="${SOURCE_URLS.geometry}" target="_blank" rel="noreferrer">2026 bureau geometry</a></p>
    `;
  }

  renderLoading();

  function cleanText(text) {
    return text.replace(/\s+/g, " ").trim();
  }

  function ordinal(n) {
    if (n === 1) return "1st";
    if (n === 2) return "2nd";
    if (n === 3) return "3rd";
    return `${n}th`;
  }

  function districtLabel(arrondissement) {
    const arr = Number(arrondissement);
    return [1, 2, 3, 4].includes(arr)
      ? "Paris Centre"
      : `${ordinal(arr)} arrondissement`;
  }

  function colorFor(name) {
    const lower = name.toLowerCase();
    if (lower.includes("grégoire") || lower.includes("gregoire")) return "#d85b4a";
    if (lower.includes("dati") || lower.includes("changer paris")) return "#2c5f8a";
    if (lower.includes("nouveau paris populaire")) return "#3e9d62";
    if (lower.includes("bournazel") || lower.includes("apaisé") || lower.includes("apaise")) return "#4c8d90";
    if (lower.includes("knafo")) return "#bc8b2c";
    if (lower.includes("retrouvons paris")) return "#6f6ca8";
    if (lower.includes("npa")) return "#bc3b31";
    if (lower.includes("lutte ouvrière") || lower.includes("lutte ouvriere")) return "#9c4e8d";
    return "#7d776f";
  }

  function shortName(name) {
    const firstChunk = cleanText(name).split(" - ")[0];
    const marker = " avec ";
    return firstChunk.toLowerCase().includes(marker)
      ? cleanText(firstChunk.split(marker)[1] || firstChunk)
      : firstChunk;
  }

  function buildRoundPayload(raw, lastUpdated) {
    const lists = raw.cy.lists
      .map((item) => {
        const name = cleanText(raw._ln[item.ln]);
        return {
          id: item.id,
          name,
          shortName: shortName(name),
          color: colorFor(name),
          cityShare: item.votes.poc,
        };
      })
      .sort((a, b) => b.cityShare - a.cityShare);

    const districts = raw.dc.map((district) => ({
      id: district.id,
      label: district.id === "1234" ? "Paris Centre" : districtLabel(Number(district.id)),
      turnoutPct: district.p.p.pr,
      registeredVoters: district.rv,
      lists: district.lists.map((entry) => ({
        id: entry.id,
        shareCast: entry.votes.poc,
        votes: entry.votes.count,
      })),
    }));

    return {
      countingComplete: Boolean(raw.cc),
      lastUpdated,
      city: {
        turnoutPct: raw.cy.p.p.pr,
        registeredVoters: raw.cy.rv,
        castVotes: raw.cy.cv,
        lists: raw.cy.lists.map((entry) => ({
          id: entry.id,
          shareCast: entry.votes.poc,
          votes: entry.votes.count,
        })),
      },
      lists,
      districts,
    };
  }

  function buildFeaturePayload(geojson, round1, round2) {
    const round1Stations = Object.values(round1.cy.ps).reduce((acc, station) => {
      acc[station.number] = station;
      return acc;
    }, {});
    const round2Stations = Object.values(round2.cy.ps).reduce((acc, station) => {
      acc[station.number] = station;
      return acc;
    }, {});

    return geojson.features.map((feature) => {
      const props = feature.properties;
      const arr = Number(props.arrondissement);
      const bureau = Number(props.num_bv);
      const stationNumber = `${String(arr).padStart(2, "0")}${String(bureau).padStart(2, "0")}`;

      function mapRound(station) {
        const lists = station.lists
          .map((item) => ({
            id: item.id,
            votes: item.votes.count,
            shareCast: item.votes.poc,
            shareRegistered: item.votes.por,
          }))
          .sort((a, b) => b.shareCast - a.shareCast);

        const lookup = lists.reduce((acc, item) => {
          acc[item.id] = item;
          return acc;
        }, {});

        return {
          districtId: station.di,
          registeredVoters: station.rv,
          castVotes: lists.reduce((sum, item) => sum + item.votes, 0),
          turnoutPct: station.pp,
          countingComplete: Boolean(station.cc),
          leaderId: lists[0]?.id || null,
          leaderShare: lists[0]?.shareCast || 0,
          lists,
          listLookup: lookup,
        };
      }

      return {
        ...feature,
        properties: {
          id_bv: props.id_bv,
          arrondissement: arr,
          bureau,
          stationNumber,
          label: `Bureau ${stationNumber}`,
          districtLabel: districtLabel(arr),
          rounds: {
            round1: mapRound(round1Stations[stationNumber]),
            round2: mapRound(round2Stations[stationNumber]),
          },
        },
      };
    });
  }

  let fetched;
  try {
    const [geojson, round1, round2] = await Promise.all([
      fetch(SOURCE_URLS.geometry).then((response) => {
        if (!response.ok) throw new Error("2026 bureau geometry request failed.");
        return response.json();
      }),
      fetch(SOURCE_URLS.round1Json).then((response) => {
        if (!response.ok) throw new Error("First-round results request failed.");
        return response.json();
      }),
      fetch(SOURCE_URLS.round2Json).then((response) => {
        if (!response.ok) throw new Error("Second-round results request failed.");
        return response.json();
      }),
    ]);

    fetched = {
      sources: {
        geometry: SOURCE_URLS.geometry,
        round1Page: SOURCE_URLS.round1Page,
        round2Page: SOURCE_URLS.round2Page,
      },
      rounds: {
        round1: buildRoundPayload(round1, "Official Ville de Paris update: 16 March 2026, 05:48"),
        round2: buildRoundPayload(round2, "Official Ville de Paris update: 23 March 2026, 01:08"),
      },
      features: buildFeaturePayload(geojson, round1, round2),
    };
  } catch (error) {
    renderError(error.message);
    return;
  }

  const data = fetched;
  const state = {
    round: "round2",
    metric: "leader",
    candidate: null,
    selectedFeatureId: null,
    hoveredFeatureId: null,
  };

  const featureIndex = new Map(data.features.map((feature) => [feature.properties.id_bv, feature]));
  const layerIndex = new Map();

  function formatNumber(value) {
    return new Intl.NumberFormat("en-GB").format(value);
  }

  function formatPct(value) {
    return `${Number(value).toFixed(1)}%`;
  }

  function getRoundMeta(roundId) {
    return data.rounds[roundId];
  }

  function getCandidateMeta(roundId, candidateId) {
    return data.rounds[roundId].lists.find((item) => item.id === candidateId);
  }

  function getFeatureRound(feature, roundId) {
    return feature.properties.rounds[roundId];
  }

  function getCurrentFeature() {
    return featureIndex.get(state.selectedFeatureId) || featureIndex.get(state.hoveredFeatureId) || null;
  }

  function getTopList(listRows) {
    return [...listRows].sort((a, b) => b.shareCast - a.shareCast)[0];
  }

  function getLeaderStats(roundId) {
    const counts = new Map();
    data.features.forEach((feature) => {
      const round = getFeatureRound(feature, roundId);
      if (!round.leaderId) return;
      counts.set(round.leaderId, (counts.get(round.leaderId) || 0) + 1);
    });
    return [...counts.entries()]
      .map(([id, count]) => ({ id, count, meta: getCandidateMeta(roundId, id) }))
      .sort((a, b) => b.count - a.count);
  }

  function getDistrictWins(roundId) {
    const wins = new Map();
    data.rounds[roundId].districts.forEach((district) => {
      const leader = getTopList(district.lists);
      if (!leader) return;
      wins.set(leader.id, (wins.get(leader.id) || 0) + 1);
    });
    return wins;
  }

  function getRange(roundId, metricId, candidateId) {
    const values = data.features
      .map((feature) => {
        const round = getFeatureRound(feature, roundId);
        if (metricId === "turnout") return round.turnoutPct;
        if (metricId === "share") return round.listLookup[candidateId]?.shareCast ?? 0;
        return round.leaderShare;
      })
      .sort((a, b) => a - b);
    return {
      min: values[0],
      mid: values[Math.floor(values.length / 2)],
      max: values[values.length - 1],
    };
  }

  function hexToRgb(hex) {
    const clean = hex.replace("#", "");
    const normalized = clean.length === 3 ? clean.split("").map((char) => char + char).join("") : clean;
    const parsed = Number.parseInt(normalized, 16);
    return {
      r: (parsed >> 16) & 255,
      g: (parsed >> 8) & 255,
      b: parsed & 255,
    };
  }

  function rgbToHex(color) {
    const toHex = (value) => value.toString(16).padStart(2, "0");
    return `#${toHex(color.r)}${toHex(color.g)}${toHex(color.b)}`;
  }

  function mixColors(start, end, t) {
    const a = hexToRgb(start);
    const b = hexToRgb(end);
    return rgbToHex({
      r: Math.round(a.r + (b.r - a.r) * t),
      g: Math.round(a.g + (b.g - a.g) * t),
      b: Math.round(a.b + (b.b - a.b) * t),
    });
  }

  function getSequentialColor(value, range, palette) {
    const span = Math.max(range.max - range.min, 0.0001);
    const t = Math.min(1, Math.max(0, (value - range.min) / span));
    return t < 0.5
      ? mixColors(palette[0], palette[1], t * 2)
      : mixColors(palette[1], palette[2], (t - 0.5) * 2);
  }

  function getStyle(feature) {
    const round = getFeatureRound(feature, state.round);
    const isActive =
      feature.properties.id_bv === state.selectedFeatureId ||
      feature.properties.id_bv === state.hoveredFeatureId;

    if (state.metric === "leader") {
      const leader = getCandidateMeta(state.round, round.leaderId);
      return {
        fillColor: leader?.color || "#999999",
        fillOpacity: Math.max(0.42, Math.min(0.92, round.leaderShare / 100)),
        color: isActive ? "#1f1a17" : "rgba(35, 25, 18, 0.38)",
        weight: isActive ? 2.2 : 0.75,
        opacity: 1,
      };
    }

    const range = getRange(state.round, state.metric, state.candidate);
    const palette =
      state.metric === "turnout"
        ? ["#fff3cf", "#f29c52", "#ae2f23"]
        : ["#e6f4ef", "#48a88c", "#0f4a5c"];
    const value =
      state.metric === "turnout"
        ? round.turnoutPct
        : round.listLookup[state.candidate]?.shareCast ?? 0;

    return {
      fillColor: getSequentialColor(value, range, palette),
      fillOpacity: 0.92,
      color: isActive ? "#1f1a17" : "rgba(35, 25, 18, 0.28)",
      weight: isActive ? 2.2 : 0.65,
      opacity: 1,
    };
  }

  function renderToggle(container, options, value, onChange) {
    container.innerHTML = "";
    options.forEach((option) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = option.label;
      button.className = option.id === value ? "active" : "";
      button.addEventListener("click", () => onChange(option.id));
      container.appendChild(button);
    });
  }

  function ensureCandidateSelection() {
    const round = getRoundMeta(state.round);
    if (!round.lists.some((item) => item.id === state.candidate)) {
      state.candidate = round.lists[0]?.id || null;
    }
  }

  function renderCandidateSelect() {
    ensureCandidateSelection();
    dom.candidateGroup.style.display = state.metric === "share" ? "grid" : "none";
    dom.candidateSelect.innerHTML = "";
    getRoundMeta(state.round).lists.forEach((candidate) => {
      const option = document.createElement("option");
      option.value = candidate.id;
      option.textContent = candidate.name;
      option.selected = candidate.id === state.candidate;
      dom.candidateSelect.appendChild(option);
    });
  }

  function renderHero() {
    dom.heroMeta.innerHTML = `
      <span class="meta-pill">903 bureau sectors</span>
      <span class="meta-pill">Live Ville de Paris feeds</span>
      <span class="meta-pill">Turnout included at bureau level</span>
    `;

    const round = getRoundMeta(state.round);
    const cityLeader = getTopList(round.city.lists);
    const cityLeaderMeta = getCandidateMeta(state.round, cityLeader.id);
    const wins = getDistrictWins(state.round);
    const bureauLeader = getLeaderStats(state.round)[0];

    const cards = [
      {
        label: "City leader",
        value: cityLeaderMeta?.name || "N/A",
        subtext: `${formatPct(cityLeader.shareCast)} of expressed votes citywide`,
      },
      {
        label: "Overall turnout",
        value: formatPct(round.city.turnoutPct),
        subtext: `${formatNumber(round.city.registeredVoters)} registered voters`,
      },
      {
        label: "Districts led",
        value: `${wins.get(cityLeader.id) || 0} / ${round.districts.length}`,
        subtext: "District-level leads across Paris",
      },
      {
        label: "Bureaux led",
        value: `${bureauLeader?.count || 0} / ${data.features.length}`,
        subtext: bureauLeader?.meta?.name || "No bureau lead data",
      },
    ];

    dom.heroCards.innerHTML = cards
      .map(
        (card) => `
          <article class="stats-card">
            <div class="stats-label">${card.label}</div>
            <div class="stats-value">${card.value}</div>
            <div class="stats-subtext">${card.subtext}</div>
          </article>
        `,
      )
      .join("");
  }

  function renderLegend() {
    const round = getRoundMeta(state.round);
    if (state.metric === "leader") {
      dom.legend.innerHTML = `
        <div class="legend-title">Leader by bureau sector</div>
        ${round.lists
          .map(
            (candidate) => `
              <div class="legend-item">
                <span class="legend-swatch" style="background:${candidate.color}"></span>
                <span>${candidate.name}</span>
                <span>${formatPct(candidate.cityShare)}</span>
              </div>
            `,
          )
          .join("")}
      `;
      return;
    }

    const range = getRange(state.round, state.metric, state.candidate);
    const candidate = getCandidateMeta(state.round, state.candidate);
    const palette =
      state.metric === "turnout"
        ? ["#fff3cf", "#f29c52", "#ae2f23"]
        : ["#e6f4ef", "#48a88c", "#0f4a5c"];
    dom.legend.innerHTML = `
      <div class="legend-title">${
        state.metric === "turnout" ? "Turnout by bureau sector" : `${candidate?.name || "Candidate"} vote share`
      }</div>
      <div class="gradient-scale" style="background: linear-gradient(90deg, ${palette.join(", ")});"></div>
      <div class="scale-labels">
        <span>${formatPct(range.min)}</span>
        <span>${formatPct(range.mid)}</span>
        <span>${formatPct(range.max)}</span>
      </div>
    `;
  }

  function getTopFeature(metric) {
    return [...data.features].sort((a, b) => {
      const roundA = getFeatureRound(a, state.round);
      const roundB = getFeatureRound(b, state.round);
      const valueA =
        metric === "turnout" ? roundA.turnoutPct : roundA.listLookup[state.candidate]?.shareCast ?? 0;
      const valueB =
        metric === "turnout" ? roundB.turnoutPct : roundB.listLookup[state.candidate]?.shareCast ?? 0;
      return valueB - valueA;
    })[0];
  }

  function renderSummary() {
    const round = getRoundMeta(state.round);
    const cityLeader = getTopList(round.city.lists);
    const cityLeaderMeta = getCandidateMeta(state.round, cityLeader.id);
    const topTurnoutFeature = getTopFeature("turnout");
    const topCandidateFeature = getTopFeature("share");
    const topTurnout = getFeatureRound(topTurnoutFeature, state.round);
    const topCandidateRound = getFeatureRound(topCandidateFeature, state.round);
    const topCandidateMeta = getCandidateMeta(state.round, state.candidate);

    dom.summaryCard.innerHTML = `
      <div class="detail-title">Round snapshot</div>
      <div class="detail-headline">${ROUND_OPTIONS.find((item) => item.id === state.round)?.label}</div>
      <p class="empty-copy">
        ${
          state.round === "round2" && !round.countingComplete
            ? "Official Ville de Paris still flags the second-round feed as counting in progress."
            : "Official Ville de Paris marks this round complete."
        }
      </p>
      <div class="summary-grid">
        <div class="summary-stat">
          <strong>City leader</strong>
          <span>${cityLeaderMeta?.name || "N/A"}</span>
        </div>
        <div class="summary-stat">
          <strong>City turnout</strong>
          <span>${formatPct(round.city.turnoutPct)}</span>
        </div>
        <div class="summary-stat">
          <strong>Highest-turnout bureau</strong>
          <span>${topTurnoutFeature.properties.label}</span>
          <div class="stats-subtext">${formatPct(topTurnout.turnoutPct)} turnout</div>
        </div>
        <div class="summary-stat">
          <strong>Strongest bureau for ${topCandidateMeta?.shortName || "selected candidate"}</strong>
          <span>${topCandidateFeature.properties.label}</span>
          <div class="stats-subtext">${formatPct(topCandidateRound.listLookup[state.candidate]?.shareCast ?? 0)} of expressed votes</div>
        </div>
      </div>
    `;
  }

  function buildResultBars(round) {
    return round.lists
      .slice(0, 6)
      .map((candidate) => {
        const meta = getCandidateMeta(state.round, candidate.id);
        return `
          <div class="result-row">
            <div class="result-line">
              <span>${meta?.name || candidate.id}</span>
              <strong>${formatPct(candidate.shareCast)}</strong>
            </div>
            <div class="bar-track">
              <div class="bar-fill" style="width:${candidate.shareCast}%;background:${meta?.color || "#999"}"></div>
            </div>
          </div>
        `;
      })
      .join("");
  }

  function renderDetail() {
    const feature = getCurrentFeature();
    if (!feature) {
      const round = getRoundMeta(state.round);
      const leader = getCandidateMeta(state.round, getTopList(round.city.lists).id);
      dom.detailCard.innerHTML = `
        <div class="detail-title">How to read the map</div>
        <div class="detail-headline">Hover or click a bureau</div>
        <p class="empty-copy">
          Each polygon is a Paris voting bureau sector. Hover to inspect the local result, click to pin it, and switch the toggles above to compare leadership, turnout, and any candidate’s bureau-level vote share.
        </p>
        <div class="summary-stat">
          <strong>Current city leader</strong>
          <span>${leader?.name || "N/A"}</span>
          <div class="stats-subtext">${formatPct(getTopList(round.city.lists).shareCast)} of expressed votes in ${ROUND_OPTIONS.find((item) => item.id === state.round)?.label.toLowerCase()}</div>
        </div>
      `;
      return;
    }

    const round = getFeatureRound(feature, state.round);
    const leader = getCandidateMeta(state.round, round.leaderId);
    dom.detailCard.innerHTML = `
      <div class="detail-title">Selected bureau</div>
      <div class="detail-headline">${feature.properties.label}</div>
      <p class="detail-meta">
        ${feature.properties.districtLabel} · ${formatNumber(round.registeredVoters)} registered voters · turnout ${formatPct(round.turnoutPct)}
      </p>
      <div class="summary-grid">
        <div class="summary-stat">
          <strong>Leader</strong>
          <span>${leader?.shortName || leader?.name || "N/A"}</span>
          <div class="stats-subtext">${formatPct(round.leaderShare)} of expressed votes</div>
        </div>
        <div class="summary-stat">
          <strong>Expressed votes</strong>
          <span>${formatNumber(round.castVotes)}</span>
          <div class="stats-subtext">${round.countingComplete ? "Counted bureau" : "Counting still flagged in the feed"}</div>
        </div>
      </div>
      <div class="detail-bars">${buildResultBars(round)}</div>
    `;
  }

  function renderSources() {
    const round = getRoundMeta(state.round);
    dom.sourceCard.innerHTML = `
      <div class="detail-title">Sources</div>
      <p class="source-copy">
        Geometry: Ville de Paris 2026 polling-sector open data. Results: official Ville de Paris 2026 election feeds for the first and second rounds.
      </p>
      <p class="source-copy">
        ${round.lastUpdated} ${
          round.countingComplete
            ? "The city feed marks this round complete."
            : "The city feed still marks this round as not fully counted."
        }
      </p>
      <p class="source-copy">
        <a href="${data.sources.geometry}" target="_blank" rel="noreferrer">2026 bureau geometry</a><br />
        <a href="${data.sources.round1Page}" target="_blank" rel="noreferrer">First-round source page</a><br />
        <a href="${data.sources.round2Page}" target="_blank" rel="noreferrer">Second-round source page</a>
      </p>
    `;
  }

  function renderMapTitle() {
    const candidate = getCandidateMeta(state.round, state.candidate);
    dom.mapTitle.textContent =
      state.metric === "leader"
        ? `${ROUND_OPTIONS.find((item) => item.id === state.round)?.label} leaders`
        : state.metric === "turnout"
          ? `${ROUND_OPTIONS.find((item) => item.id === state.round)?.label} turnout`
          : `${candidate?.name || "Candidate"} vote share`;
  }

  function refreshMap() {
    layerIndex.forEach((layer, id) => {
      layer.setStyle(getStyle(featureIndex.get(id)));
    });
  }

  function tooltipHtml(feature) {
    const round = getFeatureRound(feature, state.round);
    const leader = getCandidateMeta(state.round, round.leaderId);
    return `
      <div class="tooltip-body">
        <div class="tooltip-title">${feature.properties.label}</div>
        <div class="tooltip-subtitle">${feature.properties.districtLabel}</div>
        <div class="tooltip-grid">
          <div><strong>Turnout</strong><span>${formatPct(round.turnoutPct)}</span></div>
          <div><strong>Leader</strong><span>${leader?.shortName || leader?.name || "N/A"}</span></div>
          <div><strong>Lead share</strong><span>${formatPct(round.leaderShare)}</span></div>
          <div><strong>Registered</strong><span>${formatNumber(round.registeredVoters)}</span></div>
        </div>
      </div>
    `;
  }

  function renderAll() {
    renderCandidateSelect();
    renderToggle(dom.roundToggle, ROUND_OPTIONS, state.round, (value) => {
      state.round = value;
      ensureCandidateSelection();
      renderAll();
    });
    renderToggle(dom.metricToggle, METRIC_OPTIONS, state.metric, (value) => {
      state.metric = value;
      renderAll();
    });
    renderHero();
    renderMapTitle();
    renderLegend();
    renderSummary();
    renderDetail();
    renderSources();
    refreshMap();
  }

  const map = L.map("map", {
    zoomControl: false,
    minZoom: 11,
    maxZoom: 16,
  }).setView([48.8566, 2.3522], 12.2);

  L.control.zoom({ position: "topright" }).addTo(map);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; CARTO',
    subdomains: "abcd",
    maxZoom: 20,
  }).addTo(map);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png", {
    attribution: "",
    subdomains: "abcd",
    pane: "overlayPane",
    maxZoom: 20,
  }).addTo(map);

  const geoLayer = L.geoJSON(data.features, {
    style: getStyle,
    onEachFeature(feature, layer) {
      layerIndex.set(feature.properties.id_bv, layer);
      layer.on("mouseover", () => {
        state.hoveredFeatureId = feature.properties.id_bv;
        layer
          .bindTooltip(tooltipHtml(feature), {
            sticky: true,
            direction: "top",
            className: "custom-tooltip",
          })
          .openTooltip();
        renderDetail();
        refreshMap();
      });
      layer.on("mouseout", () => {
        state.hoveredFeatureId = null;
        renderDetail();
        refreshMap();
      });
      layer.on("click", () => {
        state.selectedFeatureId =
          state.selectedFeatureId === feature.properties.id_bv ? null : feature.properties.id_bv;
        renderDetail();
        refreshMap();
      });
    },
  }).addTo(map);

  map.fitBounds(geoLayer.getBounds(), { padding: [22, 22] });

  dom.candidateSelect.addEventListener("change", (event) => {
    state.candidate = event.target.value;
    renderAll();
  });

  dom.resetView.addEventListener("click", () => {
    state.selectedFeatureId = null;
    state.hoveredFeatureId = null;
    map.fitBounds(geoLayer.getBounds(), { padding: [22, 22] });
    renderDetail();
    refreshMap();
  });

  ensureCandidateSelection();
  renderAll();
})();

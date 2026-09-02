"use client";

import { useEffect, useMemo, useState } from "react";
import { GLYPHS, GLYPH_SYSTEMS, type GlyphRecord } from "./glyph-data";

type GlyphMetrics = {
  supported: boolean;
  width: number;
  height: number;
  aspect: number;
  density: number;
  components: number;
  holes: number;
  verticalSymmetry: number;
  horizontalSymmetry: number;
  centroidX: number;
  centroidY: number;
  orientation: number;
  boundaryComplexity: number;
  endpoints: number;
  junctions: number;
  code: string;
};

type SortKey =
  | "atlas"
  | "system"
  | "components"
  | "holes"
  | "junctions"
  | "symmetry"
  | "complexity"
  | "density"
  | "orientation"
  | "similarity";

const EMPTY_METRICS: GlyphMetrics = {
  supported: false,
  width: 0,
  height: 0,
  aspect: 1,
  density: 0,
  components: 0,
  holes: 0,
  verticalSymmetry: 0,
  horizontalSymmetry: 0,
  centroidX: 0.5,
  centroidY: 0.5,
  orientation: 0,
  boundaryComplexity: 0,
  endpoints: 0,
  junctions: 0,
  code: "ANALYZING",
};

function getIndex(x: number, y: number, width: number) {
  return y * width + x;
}

function connectedComponentCount(mask: Uint8Array, width: number, height: number) {
  const visited = new Uint8Array(mask.length);
  const queueX = new Int16Array(mask.length);
  const queueY = new Int16Array(mask.length);
  let count = 0;

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const start = getIndex(x, y, width);
      if (!mask[start] || visited[start]) continue;
      count += 1;
      let head = 0;
      let tail = 0;
      queueX[tail] = x;
      queueY[tail] = y;
      tail += 1;
      visited[start] = 1;

      while (head < tail) {
        const cx = queueX[head];
        const cy = queueY[head];
        head += 1;

        for (let dy = -1; dy <= 1; dy += 1) {
          for (let dx = -1; dx <= 1; dx += 1) {
            if (dx === 0 && dy === 0) continue;
            const nx = cx + dx;
            const ny = cy + dy;
            if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
            const idx = getIndex(nx, ny, width);
            if (mask[idx] && !visited[idx]) {
              visited[idx] = 1;
              queueX[tail] = nx;
              queueY[tail] = ny;
              tail += 1;
            }
          }
        }
      }
    }
  }

  return count;
}

function holeCount(mask: Uint8Array, width: number, height: number) {
  const visited = new Uint8Array(mask.length);
  const queueX = new Int16Array(mask.length);
  const queueY = new Int16Array(mask.length);
  let holes = 0;

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const start = getIndex(x, y, width);
      if (mask[start] || visited[start]) continue;

      let head = 0;
      let tail = 0;
      let touchesEdge = false;
      queueX[tail] = x;
      queueY[tail] = y;
      tail += 1;
      visited[start] = 1;

      while (head < tail) {
        const cx = queueX[head];
        const cy = queueY[head];
        head += 1;
        if (cx === 0 || cy === 0 || cx === width - 1 || cy === height - 1) {
          touchesEdge = true;
        }

        const neighbors = [
          [cx + 1, cy],
          [cx - 1, cy],
          [cx, cy + 1],
          [cx, cy - 1],
        ];

        for (const [nx, ny] of neighbors) {
          if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
          const idx = getIndex(nx, ny, width);
          if (!mask[idx] && !visited[idx]) {
            visited[idx] = 1;
            queueX[tail] = nx;
            queueY[tail] = ny;
            tail += 1;
          }
        }
      }

      if (!touchesEdge) holes += 1;
    }
  }

  return holes;
}

function symmetryScore(mask: Uint8Array, width: number, height: number, axis: "vertical" | "horizontal") {
  let mismatch = 0;
  let union = 0;

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const mirrorX = axis === "vertical" ? width - 1 - x : x;
      const mirrorY = axis === "horizontal" ? height - 1 - y : y;
      const a = mask[getIndex(x, y, width)];
      const b = mask[getIndex(mirrorX, mirrorY, width)];
      if (a || b) union += 1;
      if (a !== b) mismatch += 1;
    }
  }

  if (!union) return 0;
  return Math.max(0, 1 - mismatch / union);
}

function boundaryComplexity(mask: Uint8Array, width: number, height: number) {
  let ink = 0;
  let boundary = 0;

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const idx = getIndex(x, y, width);
      if (!mask[idx]) continue;
      ink += 1;
      const neighbors = [
        [x + 1, y],
        [x - 1, y],
        [x, y + 1],
        [x, y - 1],
      ];
      if (
        neighbors.some(([nx, ny]) => {
          if (nx < 0 || ny < 0 || nx >= width || ny >= height) return true;
          return mask[getIndex(nx, ny, width)] === 0;
        })
      ) {
        boundary += 1;
      }
    }
  }

  return ink ? boundary / ink : 0;
}

function thinMask(source: Uint8Array, width: number, height: number) {
  const mask = source.slice();
  const neighborsAt = (x: number, y: number) => {
    const p2 = mask[getIndex(x, y - 1, width)];
    const p3 = mask[getIndex(x + 1, y - 1, width)];
    const p4 = mask[getIndex(x + 1, y, width)];
    const p5 = mask[getIndex(x + 1, y + 1, width)];
    const p6 = mask[getIndex(x, y + 1, width)];
    const p7 = mask[getIndex(x - 1, y + 1, width)];
    const p8 = mask[getIndex(x - 1, y, width)];
    const p9 = mask[getIndex(x - 1, y - 1, width)];
    return [p2, p3, p4, p5, p6, p7, p8, p9];
  };

  const transitions = (values: number[]) => {
    let count = 0;
    for (let i = 0; i < values.length; i += 1) {
      if (values[i] === 0 && values[(i + 1) % values.length] === 1) count += 1;
    }
    return count;
  };

  for (let iteration = 0; iteration < 48; iteration += 1) {
    let changed = false;

    for (let pass = 0; pass < 2; pass += 1) {
      const remove: number[] = [];
      for (let y = 1; y < height - 1; y += 1) {
        for (let x = 1; x < width - 1; x += 1) {
          const idx = getIndex(x, y, width);
          if (!mask[idx]) continue;
          const p = neighborsAt(x, y);
          const b = p.reduce((sum, value) => sum + value, 0);
          const a = transitions(p);
          if (b < 2 || b > 6 || a !== 1) continue;

          const [p2, , p4, , p6, , p8] = p;
          const ruleA =
            pass === 0 ? p2 * p4 * p6 === 0 && p4 * p6 * p8 === 0 : p2 * p4 * p8 === 0 && p2 * p6 * p8 === 0;

          if (ruleA) remove.push(idx);
        }
      }

      if (remove.length) {
        changed = true;
        for (const idx of remove) mask[idx] = 0;
      }
    }

    if (!changed) break;
  }

  return mask;
}

function topologyCounts(skeleton: Uint8Array, width: number, height: number) {
  const junctionMask = new Uint8Array(skeleton.length);
  let endpoints = 0;

  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const idx = getIndex(x, y, width);
      if (!skeleton[idx]) continue;
      let neighbors = 0;
      for (let dy = -1; dy <= 1; dy += 1) {
        for (let dx = -1; dx <= 1; dx += 1) {
          if (dx === 0 && dy === 0) continue;
          neighbors += skeleton[getIndex(x + dx, y + dy, width)];
        }
      }
      if (neighbors === 1) endpoints += 1;
      if (neighbors >= 3) junctionMask[idx] = 1;
    }
  }

  return {
    endpoints,
    junctions: connectedComponentCount(junctionMask, width, height),
  };
}

function principalOrientation(mask: Uint8Array, width: number, height: number) {
  let count = 0;
  let meanX = 0;
  let meanY = 0;

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (!mask[getIndex(x, y, width)]) continue;
      count += 1;
      meanX += x;
      meanY += y;
    }
  }

  if (!count) return { angle: 0, centroidX: 0.5, centroidY: 0.5 };
  meanX /= count;
  meanY /= count;

  let xx = 0;
  let yy = 0;
  let xy = 0;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (!mask[getIndex(x, y, width)]) continue;
      const dx = x - meanX;
      const dy = y - meanY;
      xx += dx * dx;
      yy += dy * dy;
      xy += dx * dy;
    }
  }

  let angle = (0.5 * Math.atan2(2 * xy, xx - yy) * 180) / Math.PI;
  if (angle < 0) angle += 180;

  return {
    angle,
    centroidX: width > 1 ? meanX / (width - 1) : 0.5,
    centroidY: height > 1 ? meanY / (height - 1) : 0.5,
  };
}

function analyzeGlyph(glyph: GlyphRecord): GlyphMetrics {
  const canvas = document.createElement("canvas");
  canvas.width = 112;
  canvas.height = 112;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) return EMPTY_METRICS;

  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#111";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.font = `76px ${glyph.fontFamily}`;
  context.fillText(glyph.char, canvas.width / 2, canvas.height / 2 + 2);

  const pixels = context.getImageData(0, 0, canvas.width, canvas.height);
  let minX = canvas.width;
  let minY = canvas.height;
  let maxX = -1;
  let maxY = -1;

  for (let y = 0; y < canvas.height; y += 1) {
    for (let x = 0; x < canvas.width; x += 1) {
      const alpha = pixels.data[(y * canvas.width + x) * 4 + 3];
      if (alpha < 48) continue;
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
    }
  }

  if (maxX < minX || maxY < minY) return EMPTY_METRICS;

  const width = maxX - minX + 3;
  const height = maxY - minY + 3;
  const mask = new Uint8Array(width * height);
  let ink = 0;

  for (let y = minY - 1; y <= maxY + 1; y += 1) {
    for (let x = minX - 1; x <= maxX + 1; x += 1) {
      const localX = x - (minX - 1);
      const localY = y - (minY - 1);
      if (x < 0 || y < 0 || x >= canvas.width || y >= canvas.height) continue;
      const alpha = pixels.data[(y * canvas.width + x) * 4 + 3];
      if (alpha >= 96) {
        mask[getIndex(localX, localY, width)] = 1;
        ink += 1;
      }
    }
  }

  const components = connectedComponentCount(mask, width, height);
  const holes = holeCount(mask, width, height);
  const verticalSymmetry = symmetryScore(mask, width, height, "vertical");
  const horizontalSymmetry = symmetryScore(mask, width, height, "horizontal");
  const complexity = boundaryComplexity(mask, width, height);
  const skeleton = thinMask(mask, width, height);
  const topology = topologyCounts(skeleton, width, height);
  const orientation = principalOrientation(mask, width, height);
  const density = ink / Math.max(1, width * height);
  const aspect = width / Math.max(1, height);

  const code = [
    `C${components}`,
    `H${holes}`,
    `T${topology.endpoints}`,
    `J${topology.junctions}`,
    `V${verticalSymmetry.toFixed(2)}`,
    `X${horizontalSymmetry.toFixed(2)}`,
    `A${aspect.toFixed(2)}`,
    `O${Math.round(orientation.angle)}`,
  ].join("·");

  return {
    supported: true,
    width,
    height,
    aspect,
    density,
    components,
    holes,
    verticalSymmetry,
    horizontalSymmetry,
    centroidX: orientation.centroidX,
    centroidY: orientation.centroidY,
    orientation: orientation.angle,
    boundaryComplexity: complexity,
    endpoints: topology.endpoints,
    junctions: topology.junctions,
    code,
  };
}

function orientationDistance(a: number, b: number) {
  const direct = Math.abs(a - b);
  return Math.min(direct, 180 - direct) / 90;
}

function similarityDistance(a: GlyphMetrics, b: GlyphMetrics) {
  if (!a.supported || !b.supported) return Number.POSITIVE_INFINITY;
  const terms = [
    Math.log(Math.max(0.05, a.aspect) / Math.max(0.05, b.aspect)),
    (a.components - b.components) * 0.65,
    (a.holes - b.holes) * 0.8,
    (a.endpoints - b.endpoints) * 0.16,
    (a.junctions - b.junctions) * 0.5,
    (a.verticalSymmetry - b.verticalSymmetry) * 1.4,
    (a.horizontalSymmetry - b.horizontalSymmetry) * 1.4,
    (a.density - b.density) * 2,
    (a.boundaryComplexity - b.boundaryComplexity) * 2,
    orientationDistance(a.orientation, b.orientation),
  ];
  return Math.sqrt(terms.reduce((sum, term) => sum + term * term, 0));
}

function tagMatches(tag: string, metrics: GlyphMetrics) {
  if (!metrics.supported) return false;
  switch (tag) {
    case "closed":
      return metrics.holes > 0;
    case "open":
      return metrics.holes === 0;
    case "branched":
      return metrics.junctions > 0;
    case "multi":
      return metrics.components > 1;
    case "v-sym":
      return metrics.verticalSymmetry >= 0.82;
    case "h-sym":
      return metrics.horizontalSymmetry >= 0.82;
    case "elongated":
      return metrics.aspect < 0.62 || metrics.aspect > 1.62;
    default:
      return true;
  }
}

function metricPercent(value: number) {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

const FILTERS = [
  ["closed", "has enclosure"],
  ["open", "no enclosure"],
  ["branched", "junction"],
  ["multi", "multi-component"],
  ["v-sym", "vertical symmetry"],
  ["h-sym", "horizontal symmetry"],
  ["elongated", "elongated"],
] as const;

export default function GlyphAtlasClient() {
  const [metrics, setMetrics] = useState<Record<string, GlyphMetrics>>({});
  const [sortKey, setSortKey] = useState<SortKey>("atlas");
  const [activeFilters, setActiveFilters] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [contextVisible, setContextVisible] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      if ("fonts" in document) {
        await Promise.allSettled(
          GLYPH_SYSTEMS.map((system) => document.fonts.load(`64px "${system.primaryFont}"`)),
        );
      }

      const next: Record<string, GlyphMetrics> = {};
      for (let index = 0; index < GLYPHS.length; index += 1) {
        if (cancelled) return;
        const glyph = GLYPHS[index];
        next[glyph.id] = analyzeGlyph(glyph);

        if ((index + 1) % 24 === 0) {
          setMetrics({ ...next });
          await new Promise<void>((resolve) => window.setTimeout(resolve, 0));
        }
      }

      if (!cancelled) setMetrics(next);
    };

    run();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedGlyph = selectedId ? GLYPHS.find((glyph) => glyph.id === selectedId) ?? null : null;
  const selectedMetrics = selectedGlyph ? metrics[selectedGlyph.id] ?? EMPTY_METRICS : null;

  const visibleGlyphs = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const filtered = GLYPHS.filter((glyph) => {
      const m = metrics[glyph.id] ?? EMPTY_METRICS;
      if (
        normalizedQuery &&
        !`${glyph.id} ${glyph.systemLabel} ${glyph.unicodeLabel}`.toLowerCase().includes(normalizedQuery)
      ) {
        return false;
      }
      return activeFilters.every((filter) => tagMatches(filter, m));
    });

    return [...filtered].sort((a, b) => {
      const ma = metrics[a.id] ?? EMPTY_METRICS;
      const mb = metrics[b.id] ?? EMPTY_METRICS;
      switch (sortKey) {
        case "system":
          return a.systemLabel.localeCompare(b.systemLabel) || a.atlasOrder - b.atlasOrder;
        case "components":
          return ma.components - mb.components || a.atlasOrder - b.atlasOrder;
        case "holes":
          return ma.holes - mb.holes || a.atlasOrder - b.atlasOrder;
        case "junctions":
          return ma.junctions - mb.junctions || a.atlasOrder - b.atlasOrder;
        case "symmetry":
          return Math.max(mb.verticalSymmetry, mb.horizontalSymmetry) - Math.max(ma.verticalSymmetry, ma.horizontalSymmetry);
        case "complexity":
          return ma.boundaryComplexity - mb.boundaryComplexity;
        case "density":
          return ma.density - mb.density;
        case "orientation":
          return ma.orientation - mb.orientation;
        case "similarity":
          if (!selectedMetrics) return a.atlasOrder - b.atlasOrder;
          return similarityDistance(ma, selectedMetrics) - similarityDistance(mb, selectedMetrics);
        case "atlas":
        default:
          return a.atlasOrder - b.atlasOrder;
      }
    });
  }, [activeFilters, metrics, query, selectedMetrics, sortKey]);

  const nearest = useMemo(() => {
    if (!selectedGlyph || !selectedMetrics?.supported) return [];
    return GLYPHS.filter((glyph) => glyph.id !== selectedGlyph.id)
      .map((glyph) => ({
        glyph,
        distance: similarityDistance(metrics[glyph.id] ?? EMPTY_METRICS, selectedMetrics),
      }))
      .filter((item) => Number.isFinite(item.distance))
      .sort((a, b) => a.distance - b.distance)
      .slice(0, 8);
  }, [metrics, selectedGlyph, selectedMetrics]);

  const toggleFilter = (key: string) => {
    setActiveFilters((current) =>
      current.includes(key) ? current.filter((item) => item !== key) : [...current, key],
    );
  };

  const analyzedCount = Object.keys(metrics).length;

  return (
    <main className="glyphAtlas">
      <header className="glyphHeader">
        <div>
          <a className="backLink" href="/">Write Now / Mark</a>
          <p className="eyebrow">Glyph Atlas v0 · display engineering corpus</p>
          <h1>300 glyphs. One machine view.</h1>
          <p className="lede">
            The wall ignores meaning first. Each standardized display form is rasterized in the browser and reduced to the
            same measurements: components, enclosed voids, terminals, junctions, symmetry, density, orientation, and
            boundary complexity.
          </p>
        </div>
        <div className="corpusReadout" aria-label="Corpus status">
          <strong>{analyzedCount}</strong>
          <span>/ 300 analyzed</span>
          <small>12 comparison sets</small>
        </div>
      </header>

      <section className="methodNotice">
        <strong>Important:</strong> this first wall is the computational display layer, not the archaeological evidence
        layer. Unicode forms are being used so the algorithm and interface can be exercised at scale immediately. Mark&apos;s
        physical witnesses remain separate and will replace these display proxies system by system.
      </section>

      <section className="atlasControls" aria-label="Glyph Atlas controls">
        <label className="controlField">
          <span>Sort</span>
          <select value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}>
            <option value="atlas">Atlas order</option>
            <option value="system">Historical set</option>
            <option value="components">Component count</option>
            <option value="holes">Enclosures / holes</option>
            <option value="junctions">Junction count</option>
            <option value="symmetry">Symmetry</option>
            <option value="complexity">Boundary complexity</option>
            <option value="density">Ink density</option>
            <option value="orientation">Principal orientation</option>
            <option value="similarity" disabled={!selectedGlyph}>Similarity to selected glyph</option>
          </select>
        </label>

        <label className="controlField searchField">
          <span>Find</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="G00124, Brahmi, U+10903…"
          />
        </label>

        <button
          className={`contextToggle ${contextVisible ? "isActive" : ""}`}
          type="button"
          onClick={() => setContextVisible((current) => !current)}
        >
          {contextVisible ? "Context visible" : "Blind view"}
        </button>
      </section>

      <section className="filterRail" aria-label="Structural filters">
        {FILTERS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={activeFilters.includes(key) ? "isActive" : ""}
            onClick={() => toggleFilter(key)}
          >
            {label}
          </button>
        ))}
        {activeFilters.length > 0 && (
          <button type="button" className="clearFilters" onClick={() => setActiveFilters([])}>
            clear
          </button>
        )}
        <span className="resultCount">{visibleGlyphs.length} shown</span>
      </section>

      <section className="glyphGrid" aria-label="Glyph comparison wall">
        {visibleGlyphs.map((glyph) => {
          const m = metrics[glyph.id] ?? EMPTY_METRICS;
          const isSelected = selectedId === glyph.id;
          return (
            <button
              className={`glyphCard ${isSelected ? "isSelected" : ""}`}
              key={glyph.id}
              type="button"
              onClick={() => setSelectedId(glyph.id)}
            >
              <span className="glyphMark" style={{ fontFamily: glyph.fontFamily }}>
                {glyph.char}
              </span>
              <span className="glyphIdentity">
                <strong>{glyph.id}</strong>
                <span>{m.code}</span>
              </span>
              {contextVisible && <span className="glyphContext">{glyph.systemLabel}</span>}
            </button>
          );
        })}
      </section>

      {selectedGlyph && selectedMetrics && (
        <aside className="glyphInspector" aria-label={`Inspector for ${selectedGlyph.id}`}>
          <div className="inspectorTop">
            <div>
              <p className="eyebrow">Selected structure</p>
              <h2>{selectedGlyph.id}</h2>
            </div>
            <button type="button" className="closeInspector" onClick={() => setSelectedId(null)} aria-label="Close inspector">
              ×
            </button>
          </div>

          <div className="inspectorHero">
            <span style={{ fontFamily: selectedGlyph.fontFamily }}>{selectedGlyph.char}</span>
            <code>{selectedMetrics.code}</code>
          </div>

          <button
            type="button"
            className="similarityButton"
            onClick={() => setSortKey("similarity")}
            disabled={!selectedMetrics.supported}
          >
            Reorder the whole wall from this glyph
          </button>

          <div className="metricGrid">
            <div><span>components</span><strong>{selectedMetrics.components}</strong></div>
            <div><span>enclosures</span><strong>{selectedMetrics.holes}</strong></div>
            <div><span>terminals</span><strong>{selectedMetrics.endpoints}</strong></div>
            <div><span>junctions</span><strong>{selectedMetrics.junctions}</strong></div>
            <div><span>aspect</span><strong>{selectedMetrics.aspect.toFixed(2)}</strong></div>
            <div><span>orientation</span><strong>{Math.round(selectedMetrics.orientation)}°</strong></div>
          </div>

          <div className="metricBars">
            <label>
              <span>vertical symmetry <b>{metricPercent(selectedMetrics.verticalSymmetry)}</b></span>
              <i style={{ width: metricPercent(selectedMetrics.verticalSymmetry) }} />
            </label>
            <label>
              <span>horizontal symmetry <b>{metricPercent(selectedMetrics.horizontalSymmetry)}</b></span>
              <i style={{ width: metricPercent(selectedMetrics.horizontalSymmetry) }} />
            </label>
            <label>
              <span>ink density <b>{metricPercent(selectedMetrics.density)}</b></span>
              <i style={{ width: metricPercent(selectedMetrics.density) }} />
            </label>
            <label>
              <span>boundary complexity <b>{metricPercent(selectedMetrics.boundaryComplexity)}</b></span>
              <i style={{ width: metricPercent(selectedMetrics.boundaryComplexity) }} />
            </label>
          </div>

          <div className="decomposition">
            <p className="eyebrow">Machine decomposition</p>
            <div className="decompFlow">
              <span>RASTER</span>
              <b>→</b>
              <span>C{selectedMetrics.components}</span>
              <b>→</b>
              <span>H{selectedMetrics.holes}</span>
              <b>→</b>
              <span>T{selectedMetrics.endpoints}</span>
              <b>→</b>
              <span>J{selectedMetrics.junctions}</span>
            </div>
            <p>
              This is deliberately pre-semantic. “Hole” means a bounded background region in the rendered form;
              “junction” means a clustered branch/crossing candidate after skeletonization. Neither is yet a historical
              interpretation.
            </p>
          </div>

          <div className="nearest">
            <div className="nearestHeading">
              <p className="eyebrow">Structurally nearest</p>
              <small>same raster metric space</small>
            </div>
            <div className="nearestGrid">
              {nearest.map(({ glyph, distance }) => (
                <button key={glyph.id} type="button" onClick={() => setSelectedId(glyph.id)}>
                  <span style={{ fontFamily: glyph.fontFamily }}>{glyph.char}</span>
                  <strong>{glyph.id}</strong>
                  <small>{distance.toFixed(2)}</small>
                  {contextVisible && <em>{glyph.systemLabel}</em>}
                </button>
              ))}
            </div>
          </div>

          <details className="contextDetails" open={contextVisible}>
            <summary>Display provenance</summary>
            <p><strong>{selectedGlyph.systemLabel}</strong><br />{selectedGlyph.context}</p>
            <p>{selectedGlyph.unicodeLabel}</p>
            <p>{selectedGlyph.displayBasis}</p>
            <a href={selectedGlyph.sourceUrl} target="_blank" rel="noreferrer">Unicode display source</a>
          </details>
        </aside>
      )}
    </main>
  );
}

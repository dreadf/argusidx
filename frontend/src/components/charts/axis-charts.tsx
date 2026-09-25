"use client";

import type { ReactNode } from "react";
import { idNum, signedPct } from "@/lib/format";
import { useWidth } from "./use-width";

/**
 * Charts drawn to a fixed recipe, agreed after the first round of user
 * feedback ("the axes and percentages are not clear"):
 *   - the chart's title is a plain question, written by the caller
 *   - every axis has a title with its unit; ticks sit at gridlines
 *   - values are printed on the marks; series are labelled directly,
 *     never through a legend the reader has to look up
 *   - zero baseline everywhere, no truncated axes, no decoration
 * All text is drawn at its real pixel size (width comes from the
 * container), so nothing shrinks on a phone.
 */

const MUTED = "var(--viz-ink-muted)";
const INK = "var(--viz-ink-primary)";
const SOFT = "#B4BFD1";
const BLUE = "var(--viz-chart-blue)";
const GREY = "#7f8ca3";
const ACCENT = "var(--viz-accent)";
const GRID = "rgba(255,255,255,0.09)";

interface Geo {
  W: number;
  H: number;
  ml: number;
  mr: number;
  mt: number;
  ph: number;
  pw: number;
  base: number;
}

function geo(W: number, o: { ph?: number; ml?: number; mr?: number; mt?: number; mb?: number } = {}): Geo {
  const ph = o.ph ?? 170;
  const ml = o.ml ?? 54;
  const mr = o.mr ?? 14;
  const mt = o.mt ?? 34;
  const mb = o.mb ?? 78;
  return { W, H: mt + ph + mb, ml, mr, mt, ph, pw: W - ml - mr, base: mt + ph };
}

function T({
  x,
  y,
  children,
  size = 11.5,
  fill = MUTED,
  anchor = "middle",
  weight = 400,
  mono = false,
  rotate,
}: {
  x: number;
  y: number;
  children: ReactNode;
  size?: number;
  fill?: string;
  anchor?: "start" | "middle" | "end";
  weight?: number;
  mono?: boolean;
  rotate?: number;
}) {
  return (
    <text
      x={x}
      y={y}
      textAnchor={anchor}
      fontSize={size}
      fontWeight={weight}
      fill={fill}
      fontFamily={mono ? "var(--font-geist-mono), monospace" : undefined}
      transform={rotate ? `rotate(${rotate} ${x} ${y})` : undefined}
    >
      {children}
    </text>
  );
}

function YGrid({ g, ticks, y, fmt, title }: { g: Geo; ticks: number[]; y: (v: number) => number; fmt: (v: number) => string; title: string }) {
  return (
    <>
      {ticks.map((v) => (
        <g key={v}>
          <line x1={g.ml} y1={y(v)} x2={g.W - g.mr} y2={y(v)} stroke={GRID} />
          <T x={g.ml - 8} y={y(v) + 4} anchor="end">
            {fmt(v)}
          </T>
        </g>
      ))}
      <T x={13} y={g.mt + g.ph / 2} weight={500} rotate={-90}>
        {title}
      </T>
    </>
  );
}

function Svg({ g, children, label }: { g: Geo; children: ReactNode; label: string }) {
  return (
    <svg viewBox={`0 0 ${g.W} ${g.H}`} width="100%" height={g.H} role="img" aria-label={label} className="block overflow-visible">
      {children}
    </svg>
  );
}

/* ---------------- columns ---------------- */

export interface ColumnItem {
  l1: string;
  l2?: string;
  value: number;
  text: string;
}

export function AxisColumns({
  items,
  ymax,
  step,
  yTitle,
  xTitle,
  unit = "%",
  refLine,
  colors,
  label,
}: {
  items: ColumnItem[];
  ymax: number;
  step: number;
  yTitle: string;
  xTitle: string;
  unit?: string;
  refLine?: { value: number; line1: string; line2?: string };
  colors?: string[];
  label: string;
}) {
  const { ref, width } = useWidth();
  const g = geo(width, { mr: refLine ? 66 : 14 });
  const y = (v: number) => g.mt + g.ph * (1 - v / ymax);
  const ticks: number[] = [];
  for (let v = 0; v <= ymax; v += step) ticks.push(v);
  const slot = g.pw / items.length;
  const bw = Math.min(56, slot * 0.5);
  return (
    <div ref={ref} className="w-full">
      <Svg g={g} label={label}>
        <YGrid g={g} ticks={ticks} y={y} fmt={(v) => `${v}${unit}`} title={yTitle} />
        {items.map((it, i) => {
          const cx = g.ml + slot * (i + 0.5);
          return (
            <g key={it.l1 + i}>
              <rect x={cx - bw / 2} y={y(it.value)} width={bw} height={g.base - y(it.value)} rx={3} fill={colors?.[i] ?? BLUE} />
              <T x={cx} y={y(it.value) - 9} size={14} fill={INK} weight={700} mono>
                {it.text}
              </T>
              <T x={cx} y={g.base + 20} size={12} fill={it.l2 ? INK : MUTED}>
                {it.l1}
              </T>
              {it.l2 && (
                <T x={cx} y={g.base + 37}>
                  {it.l2}
                </T>
              )}
            </g>
          );
        })}
        {refLine && (
          <>
            <line x1={g.ml} y1={y(refLine.value)} x2={g.W - g.mr} y2={y(refLine.value)} stroke={ACCENT} strokeWidth={1.5} strokeDasharray="5 4" />
            <T x={g.W - g.mr + 6} y={y(refLine.value) - 3} anchor="start" fill={ACCENT} weight={600}>
              {refLine.line1}
            </T>
            {refLine.line2 && (
              <T x={g.W - g.mr + 6} y={y(refLine.value) + 14} anchor="start" fill={ACCENT} weight={600}>
                {refLine.line2}
              </T>
            )}
          </>
        )}
        <T x={g.ml + g.pw / 2} y={g.H - 6} weight={500}>
          {xTitle}
        </T>
      </Svg>
    </div>
  );
}

/* ---------------- floating range (falls by size) ---------------- */

export interface RangeGroup {
  l1: string;
  l2?: string;
  median: number;
  p25: number;
  p75: number;
}

export function RangeChart({ groups, yTitle, xTitle, floor = -80, label }: { groups: RangeGroup[]; yTitle: string; xTitle: string; floor?: number; label: string }) {
  const { ref, width } = useWidth();
  const g = geo(width, { mb: 92 });
  const y = (v: number) => g.mt + g.ph * (-v / -floor);
  const ticks = [0, floor / 4, floor / 2, (floor * 3) / 4, floor];
  const slot = g.pw / groups.length;
  const bw = Math.min(34, slot * 0.42);
  return (
    <div ref={ref} className="w-full">
      <Svg g={g} label={label}>
        <YGrid g={g} ticks={ticks} y={y} fmt={(v) => (v === 0 ? "0%" : `${v}%`)} title={yTitle} />
        {groups.map((gr, i) => {
          const cx = g.ml + slot * (i + 0.5);
          return (
            <g key={gr.l1}>
              <rect x={cx - bw / 2} y={y(gr.p75)} width={bw} height={y(gr.p25) - y(gr.p75)} rx={3} fill={BLUE} opacity={0.55} />
              <line x1={cx - bw / 2 - 5} y1={y(gr.median)} x2={cx + bw / 2 + 5} y2={y(gr.median)} stroke="#fff" strokeWidth={3} strokeLinecap="round" />
              <T x={cx} y={g.base + 20} size={12} fill={INK}>
                {gr.l1}
              </T>
              {gr.l2 && (
                <T x={cx} y={g.base + 36}>
                  {gr.l2}
                </T>
              )}
              <T x={cx} y={g.base + 56} size={13.5} fill={INK} weight={700} mono>
                {signedPct(gr.median)}
              </T>
            </g>
          );
        })}
        <T x={g.ml - 6} y={g.base + 50} anchor="end">
          Nilai
        </T>
        <T x={g.ml - 6} y={g.base + 67} anchor="end">
          tengah
        </T>
        <T x={g.ml + g.pw / 2} y={g.H - 6} weight={500}>
          {xTitle}
        </T>
      </Svg>
    </div>
  );
}

/* ---------------- two labelled lines (IPO boards) ---------------- */

export function TwoLineChart({
  categories,
  a,
  b,
  yTitle,
  xTitle,
  ref50,
  label,
}: {
  categories: string[];
  a: { name: string; values: number[] };
  b: { name: string; values: number[] };
  yTitle: string;
  xTitle: string;
  ref50: string;
  label: string;
}) {
  const { ref, width } = useWidth();
  const g = geo(width, { ph: 190, mr: 16, mb: 62 });
  const y = (v: number) => g.mt + g.ph * (1 - v / 100);
  const xs = categories.map((_, i) => g.ml + (g.pw * (i + 0.5)) / categories.length);
  const line = (vals: number[]) => vals.map((v, i) => `${xs[i].toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <div ref={ref} className="w-full">
      <Svg g={g} label={label}>
        <YGrid g={g} ticks={[0, 25, 50, 75, 100]} y={y} fmt={(v) => `${v}%`} title={yTitle} />
        <line x1={g.ml} y1={y(50)} x2={g.W - g.mr} y2={y(50)} stroke={ACCENT} strokeWidth={1.5} strokeDasharray="5 4" />
        <T x={g.ml + 4} y={y(50) - 7} anchor="start" fill={ACCENT} weight={600}>
          {ref50}
        </T>
        <polyline points={line(a.values)} fill="none" stroke={BLUE} strokeWidth={3} />
        <polyline points={line(b.values)} fill="none" stroke={GREY} strokeWidth={3} />
        {a.values.map((v, i) => (
          <g key={`a${i}`}>
            <circle cx={xs[i]} cy={y(v)} r={5} fill={BLUE} />
            <T x={xs[i]} y={y(v) - 12} size={13.5} fill={INK} weight={700} mono>
              {`${idNum(v, 0)}%`}
            </T>
          </g>
        ))}
        {b.values.map((v, i) => (
          <g key={`b${i}`}>
            <circle cx={xs[i]} cy={y(v)} r={5} fill={GREY} />
            <T x={xs[i]} y={y(v) + 24} size={13.5} fill={INK} weight={700} mono>
              {`${idNum(v, 0)}%`}
            </T>
          </g>
        ))}
        <T x={xs[xs.length - 1] + 8} y={y(a.values[a.values.length - 1]) - 30} anchor="end" fill="#8FB4EE" weight={700} size={12.5}>
          {a.name}
        </T>
        <T x={xs[xs.length - 1] + 8} y={y(b.values[b.values.length - 1]) + 46} anchor="end" fill="#b4bfd1" weight={700} size={12.5}>
          {b.name}
        </T>
        {categories.map((c, i) => (
          <T key={c} x={xs[i]} y={g.base + 20} size={12} fill={INK}>
            {c}
          </T>
        ))}
        <T x={g.ml + g.pw / 2} y={g.H - 6} weight={500}>
          {xTitle}
        </T>
      </Svg>
    </div>
  );
}

/* ---------------- distribution (Peringkat) ---------------- */

export function DistChart({ bins, median, medianLabel, yTitle, xTitle, label }: { bins: number[]; median: number; medianLabel: string; yTitle: string; xTitle: string; label: string }) {
  const { ref, width } = useWidth();
  const g = geo(width, { mb: 70 });
  const ymax = Math.ceil(Math.max(...bins) / 50) * 50;
  const y = (v: number) => g.mt + g.ph * (1 - v / ymax);
  const slot = g.pw / bins.length;
  const bw = slot * 0.78;
  const ticks: number[] = [];
  for (let v = 0; v <= ymax; v += 50) ticks.push(v);
  const mx = g.ml + median * bins.length * slot;
  return (
    <div ref={ref} className="w-full">
      <Svg g={g} label={label}>
        <YGrid g={g} ticks={ticks} y={y} fmt={(v) => String(v)} title={yTitle} />
        {bins.map((v, i) => {
          const x = g.ml + i * slot + (slot - bw) / 2;
          return (
            <g key={i}>
              <rect x={x} y={y(v)} width={bw} height={g.base - y(v)} rx={2.5} fill={i >= 2 && i <= 5 ? BLUE : "#3a5a94"} />
              <T x={x + bw / 2} y={y(v) - 7} fill={INK} weight={600} mono>
                {v}
              </T>
            </g>
          );
        })}
        {[0, 2, 4, 6, 8, 10].map((i) => (
          <T key={i} x={g.ml + i * slot} y={g.base + 18} anchor={i === 10 ? "end" : "middle"}>
            {i === 0 ? "0%" : `-${i * 10}%`}
          </T>
        ))}
        <path d={`M${mx - 6},${g.base + 34} L${mx + 6},${g.base + 34} L${mx},${g.base + 27} Z`} fill={ACCENT} />
        <T x={mx} y={g.base + 49} fill={ACCENT} weight={600}>
          {medianLabel}
        </T>
        <T x={g.ml + g.pw / 2} y={g.H - 6} weight={500}>
          {xTitle}
        </T>
      </Svg>
    </div>
  );
}

/* ---------------- ROE vs sector (stock page) ---------------- */

/** A readable axis for arbitrary data: at most about five intervals, whole-number-friendly steps, always including zero. */
export function niceScale(lo: number, hi: number): { ymin: number; ymax: number; step: number } {
  const min = Math.min(0, lo);
  const max = Math.max(0, hi);
  const span = Math.max(max - min, 1);
  const raw = span / 5;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / mag;
  const step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10) * mag;
  return { ymin: Math.floor(min / step) * step, ymax: Math.ceil(max / step) * step, step };
}

export function CompareLines({
  years,
  own,
  sector,
  ownLabel,
  sectorLabel,
  yTitle,
  xTitle,
  label,
}: {
  years: number[];
  own: (number | null)[];
  sector: (number | null)[];
  ownLabel: string;
  sectorLabel: string;
  yTitle: string;
  xTitle: string;
  label: string;
}) {
  const { ref, width } = useWidth();
  const g = geo(width, { ph: 150, mt: 30, mb: 64 });
  const all = [...own, ...sector].filter((v): v is number => v !== null);
  const { ymin, ymax, step } = niceScale(Math.min(...all, 0), Math.max(...all, 5));
  const y = (v: number) => g.mt + g.ph * (1 - (v - ymin) / (ymax - ymin));
  const xs = years.map((_, i) => g.ml + (g.pw * (i + 0.5)) / years.length);
  const ticks: number[] = [];
  for (let v = ymin; v <= ymax + step / 2; v += step) ticks.push(Math.round(v * 100) / 100);
  const pts = (vals: (number | null)[]) => vals.map((v, i) => (v === null ? null : `${xs[i].toFixed(1)},${y(v).toFixed(1)}`)).filter(Boolean).join(" ");
  const lastIdx = (vals: (number | null)[]) => vals.map((v, i) => (v === null ? -1 : i)).reduce((a, b) => Math.max(a, b), -1);
  const lo = lastIdx(own);
  const ls = lastIdx(sector);
  return (
    <div ref={ref} className="w-full">
      <Svg g={g} label={label}>
        <YGrid g={g} ticks={ticks} y={y} fmt={(v) => `${idNum(v, 0)}%`} title={yTitle} />
        <polyline points={pts(own)} fill="none" stroke={BLUE} strokeWidth={2.6} />
        <polyline points={pts(sector)} fill="none" stroke={GREY} strokeWidth={2.4} strokeDasharray="5 4" />
        {own.map((v, i) => v !== null && <circle key={`o${i}`} cx={xs[i]} cy={y(v)} r={4} fill={BLUE} />)}
        {sector.map((v, i) => v !== null && <circle key={`s${i}`} cx={xs[i]} cy={y(v)} r={3.5} fill={GREY} />)}
        {own[0] !== null && (
          <T x={xs[0] - 6} y={y(own[0] as number) - 14} anchor="start" fill={INK} weight={700} size={12} mono>
            {`${ownLabel} ${idNum(own[0] as number)}%`}
          </T>
        )}
        {lo >= 0 && (
          <T x={xs[lo] + 6} y={y(own[lo] as number) - 14} anchor="end" fill={INK} weight={700} size={12} mono>
            {`${idNum(own[lo] as number)}%`}
          </T>
        )}
        {sector[0] !== null && (
          <T x={xs[0] - 6} y={y(sector[0] as number) + 20} anchor="start" fill={SOFT} weight={600}>
            {`${sectorLabel} ${idNum(sector[0] as number)}%`}
          </T>
        )}
        {ls >= 0 && (
          <T x={xs[ls] + 6} y={y(sector[ls] as number) + 20} anchor="end" fill={SOFT} weight={600}>
            {`${idNum(sector[ls] as number)}%`}
          </T>
        )}
        {years.map((yr, i) => (
          <T key={yr} x={xs[i]} y={g.base + 20}>
            {yr}
          </T>
        ))}
        <T x={g.ml + g.pw / 2} y={g.H - 6} weight={500}>
          {xTitle}
        </T>
      </Svg>
    </div>
  );
}

/* ---------------- market value line (Home) ---------------- */

export function MarketLine({ series, maxLabel, yTitle, label }: { series: { date: string; value: number }[]; maxLabel: string; yTitle: string; label: string }) {
  const { ref, width } = useWidth();
  const g = geo(width, { ph: 150, ml: 70, mt: 26, mb: 44 });
  let imax = 0;
  series.forEach((s, i) => {
    if (s.value > series[imax].value) imax = i;
  });
  // Zero baseline (no truncated axis): 0 up to the next 5,000 above the peak.
  const hi = Math.ceil(series[imax].value / 1e12 / 5000) * 5000;
  const y = (v: number) => g.mt + g.ph * (1 - v / hi);
  const n = series.length - 1;
  const x = (i: number) => g.ml + (g.pw * i) / n;
  const points = series.map((s, i) => `${x(i).toFixed(1)},${y(s.value / 1e12).toFixed(1)}`).join(" ");
  const years: Record<string, number> = {};
  series.forEach((s, i) => {
    const yr = s.date.slice(0, 4);
    if (!(yr in years)) years[yr] = i;
  });
  const ticks: number[] = [];
  for (let v = 0; v <= hi; v += 5000) ticks.push(v);
  return (
    <div ref={ref} className="w-full">
      <Svg g={g} label={label}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={g.ml} y1={y(v)} x2={g.W - g.mr} y2={y(v)} stroke={GRID} />
            <T x={g.ml - 8} y={y(v) + 4} anchor="end">
              {idNum(v, 0)}
            </T>
          </g>
        ))}
        <T x={12} y={g.mt + g.ph / 2} weight={500} rotate={-90}>
          {yTitle}
        </T>
        <polyline points={points} fill="none" stroke={BLUE} strokeWidth={2.2} strokeLinejoin="round" />
        <circle cx={x(imax)} cy={y(series[imax].value / 1e12)} r={4} fill={BLUE} />
        <T x={x(imax)} y={y(series[imax].value / 1e12) - 9} fill={INK} weight={600}>
          {maxLabel}
        </T>
        <circle cx={x(n)} cy={y(series[n].value / 1e12)} r={4.5} fill="#fff" stroke={BLUE} strokeWidth={2} />
        {Object.entries(years).map(([yr, i]) => (
          <T key={yr} x={x(i) + (yr === Object.keys(years)[0] ? 10 : 0)} y={g.base + 18}>
            {yr}
          </T>
        ))}
      </Svg>
    </div>
  );
}

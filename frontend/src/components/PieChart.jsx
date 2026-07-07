// A dependency-free SVG pie chart. Each slice is a wedge; the percentage is
// printed inside the slice. A legend beneath maps colour -> label -> ₹value + %.
//
// Props:
//   labels: string[]
//   values: number[]   (₹ amounts; their sum is treated as 100%)

const COLORS = [
  "#10b981", // emerald
  "#3b82f6", // blue
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#ef4444", // red
  "#14b8a6", // teal
  "#ec4899", // pink
  "#eab308", // yellow
];

const SIZE = 220;
const R = 96;
const CX = SIZE / 2;
const CY = SIZE / 2;

function polar(cx, cy, r, angle) {
  return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
}

function formatINR(n) {
  return "₹" + (Number(n) || 0).toLocaleString("en-IN");
}

export default function PieChart({ labels = [], values = [] }) {
  const nums = values.map((v) => Math.max(Number(v) || 0, 0));
  const total = nums.reduce((a, b) => a + b, 0);

  if (total <= 0) return null;

  // Build slices with cumulative angles, starting at the top (-90°).
  let angle = -Math.PI / 2;
  const slices = nums.map((value, i) => {
    const frac = value / total;
    const start = angle;
    const end = angle + frac * 2 * Math.PI;
    angle = end;

    const color = COLORS[i % COLORS.length];
    const pct = Math.round(frac * 100);

    // label position: along the bisector, partway out from the centre
    const mid = (start + end) / 2;
    const [lx, ly] = polar(CX, CY, R * 0.62, mid);

    let path;
    if (frac >= 0.9999) {
      // single full-circle slice — draw as two arcs to avoid a degenerate wedge
      path = `M ${CX - R} ${CY} A ${R} ${R} 0 1 1 ${CX + R} ${CY} A ${R} ${R} 0 1 1 ${CX - R} ${CY} Z`;
    } else {
      const [x1, y1] = polar(CX, CY, R, start);
      const [x2, y2] = polar(CX, CY, R, end);
      const largeArc = frac > 0.5 ? 1 : 0;
      path = `M ${CX} ${CY} L ${x1} ${y1} A ${R} ${R} 0 ${largeArc} 1 ${x2} ${y2} Z`;
    }

    return { value, color, pct, path, lx, ly, label: labels[i] ?? `Item ${i + 1}` };
  });

  return (
    <div className="pie">
      <svg
        className="pie-svg"
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        width={SIZE}
        height={SIZE}
        role="img"
        aria-label="Income allocation pie chart"
      >
        {slices.map((s, i) => (
          <path key={i} d={s.path} fill={s.color} className="pie-slice" />
        ))}
        {slices.map((s, i) =>
          s.pct >= 6 ? (
            <text
              key={`t${i}`}
              x={s.lx}
              y={s.ly}
              className="pie-pct"
              textAnchor="middle"
              dominantBaseline="central"
            >
              {s.pct}%
            </text>
          ) : null
        )}
      </svg>

      <ul className="pie-legend">
        {slices.map((s, i) => (
          <li key={i} className="pie-legend-item">
            <span className="pie-swatch" style={{ background: s.color }} />
            <span className="pie-legend-label">{s.label}</span>
            <span className="pie-legend-value">
              {formatINR(s.value)} <span className="pie-legend-pct">· {s.pct}%</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

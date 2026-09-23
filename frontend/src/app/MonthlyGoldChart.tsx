import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const numberFormat = new Intl.NumberFormat("pt-BR");

interface MonthlyGoldPoint {
  day: number;
  gold: number;
  pveBags: number;
  bagValueGold: number;
  goldEquivalent: number;
}

function GoldTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ payload: MonthlyGoldPoint }>;
  label?: number | string;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="monthly-chart-tooltip">
      <strong>Dia {label}: {numberFormat.format(point.goldEquivalent)} gold equivalente</strong>
      <span>{numberFormat.format(point.gold)} gold + {numberFormat.format(point.pveBags)} Sacos PvE</span>
      {point.pveBags > 0 && (
        <small>
          Sacos: {point.bagValueGold > 0 ? `~${numberFormat.format(point.bagValueGold)} gold pela cotação atual` : "sem cotação para valorar"}
        </small>
      )}
    </div>
  );
}

export default function MonthlyGoldChart({ data }: { data: MonthlyGoldPoint[] }) {
  return <div className="monthly-chart" aria-label="Gold equivalente obtido por dia no mês">
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 8, right: 14, bottom: 0, left: -10 }}>
        <defs><linearGradient id="goldArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#7286ff" stopOpacity={0.42} /><stop offset="100%" stopColor="#7286ff" stopOpacity={0.02} /></linearGradient></defs>
        <CartesianGrid vertical={false} stroke="rgba(151,178,204,.08)" />
        <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: "#8293a5", fontSize: 9 }} />
        <YAxis width={42} axisLine={false} tickLine={false} tick={{ fill: "#8293a5", fontSize: 9 }} tickFormatter={(value: number) => `${Math.round(value / 1000)}k`} />
        <Tooltip content={<GoldTooltip />} />
        <Area type="monotone" dataKey="goldEquivalent" stroke="#7488ff" strokeWidth={2} fill="url(#goldArea)" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  </div>;
}

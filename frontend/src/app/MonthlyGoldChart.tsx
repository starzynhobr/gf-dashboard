import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const numberFormat = new Intl.NumberFormat("pt-BR");

export default function MonthlyGoldChart({ data }: { data: Array<{ day: number; gold: number }> }) {
  return <div className="monthly-chart" aria-label="Ouro obtido por dia no mês">
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 8, right: 14, bottom: 0, left: -10 }}>
        <defs><linearGradient id="goldArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#7286ff" stopOpacity={0.42} /><stop offset="100%" stopColor="#7286ff" stopOpacity={0.02} /></linearGradient></defs>
        <CartesianGrid vertical={false} stroke="rgba(151,178,204,.08)" />
        <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: "#8293a5", fontSize: 9 }} />
        <YAxis width={42} axisLine={false} tickLine={false} tick={{ fill: "#8293a5", fontSize: 9 }} tickFormatter={(value: number) => `${Math.round(value / 1000)}k`} />
        <Tooltip formatter={(value) => numberFormat.format(Number(value))} labelFormatter={(day) => `Dia ${day}`} contentStyle={{ background: "#0c2232", border: "1px solid #294054", borderRadius: 8, fontSize: 11 }} />
        <Area type="monotone" dataKey="gold" stroke="#7488ff" strokeWidth={2} fill="url(#goldArea)" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  </div>;
}

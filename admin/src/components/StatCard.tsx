interface StatCardProps {
  icon: string;
  label: string;
  value: number | string;
  subtitle?: string;
  color?: string;
}

export default function StatCard({ icon, label, value, subtitle, color }: StatCardProps) {
  return (
    <div className="stat-card" style={color ? { borderTopColor: color } : undefined}>
      <div className="stat-card-icon" style={color ? { background: color + '15', color } : undefined}>
        {icon}
      </div>
      <div className="stat-card-body">
        <div className="stat-card-value">{typeof value === 'number' ? value.toLocaleString() : value}</div>
        <div className="stat-card-label">{label}</div>
        {subtitle && <div className="stat-card-subtitle">{subtitle}</div>}
      </div>
    </div>
  )
}

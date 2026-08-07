type StatChipProps = {
  label: string
  value: string
}

export function StatChip({ label, value }: StatChipProps) {
  return (
    <div className="stat-chip">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  )
}

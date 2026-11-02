import type { FindingSeverity } from '@/lib/types'

const config: Record<FindingSeverity, { label: string; className: string }> = {
  critical: { label: 'Critical', className: 'badge badge-critical' },
  high: { label: 'High', className: 'badge badge-high' },
  medium: { label: 'Medium', className: 'badge badge-medium' },
  low: { label: 'Low', className: 'badge badge-low' },
}

export default function SeverityBadge({ severity }: { severity: FindingSeverity }) {
  const { label, className } = config[severity]
  return <span className={className}>{label}</span>
}

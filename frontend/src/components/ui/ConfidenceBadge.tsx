import { cn } from '@/lib/utils';

export interface ConfidenceBadgeProps {
  /** 0–1 confidence score. Thresholds are illustrative — real thresholds
   * belong to the extraction phase once real scores exist. */
  score: number;
  className?: string;
}

function bucketFor(score: number): { label: string; classes: string } {
  if (score >= 0.85) {
    return { label: 'High', classes: 'bg-status-approved-bg text-status-approved' };
  }
  if (score >= 0.6) {
    return { label: 'Medium', classes: 'bg-status-review-bg text-status-review' };
  }
  return { label: 'Low', classes: 'bg-status-failed-bg text-status-failed' };
}

export function ConfidenceBadge({ score, className }: ConfidenceBadgeProps) {
  const clamped = Math.min(1, Math.max(0, score));
  const { label, classes } = bucketFor(clamped);
  const percent = Math.round(clamped * 100);

  return (
    <span
      className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', classes, className)}
      title={`Confidence: ${percent}%`}
    >
      {label} · {percent}%
    </span>
  );
}

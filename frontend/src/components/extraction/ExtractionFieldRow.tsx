import { useEffect, useState, type KeyboardEvent } from 'react';
import { Check, X } from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge';
import { cn } from '@/lib/utils';
import type { ExtractedField } from '@/features/extraction/types';

export interface ExtractionFieldRowProps {
  field: ExtractedField;
  isSelected: boolean;
  isEditable: boolean;
  isSaving: boolean;
  onSelect: (field: ExtractedField) => void;
  onSave: (field: ExtractedField, value: string) => void;
  onDirtyChange: (fieldId: string, isDirty: boolean) => void;
}

/** One editable extracted field. Local `draft` state is separate from
 * the server value so unsaved edits are visible (and can be discarded
 * or protected against navigating away — see DocumentReview's
 * unsaved-changes guard) rather than firing a correction on every
 * keystroke. */
export function ExtractionFieldRow({
  field,
  isSelected,
  isEditable,
  isSaving,
  onSelect,
  onSave,
  onDirtyChange,
}: ExtractionFieldRowProps) {
  const [draft, setDraft] = useState(field.display_value);
  const isDirty = draft !== field.display_value;

  useEffect(() => {
    onDirtyChange(field.id, isDirty);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [field.id, isDirty]);

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter' && isDirty) {
      onSave(field, draft);
    }
    if (event.key === 'Escape') {
      setDraft(field.display_value);
    }
  }

  return (
    <div
      className={cn(
        'rounded-lg border p-3 transition-colors duration-fast',
        isSelected ? 'border-primary bg-primary-soft/40' : 'border-border bg-card',
      )}
      onFocus={() => onSelect(field)}
      onClick={() => onSelect(field)}
    >
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <label htmlFor={`field-${field.id}`} className="text-sm font-medium text-text-primary">
          {field.label}
          {field.is_required && <span className="ml-1 text-status-failed">*</span>}
        </label>
        {field.confidence !== null && <ConfidenceBadge score={field.confidence} />}
      </div>

      <div className="flex items-center gap-2">
        <Input
          id={`field-${field.id}`}
          value={draft}
          disabled={!isEditable}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={field.is_required ? 'Required — not found' : 'Not found'}
        />
        {isEditable && isDirty && (
          <>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-label={`Save ${field.label}`}
              isLoading={isSaving}
              onClick={() => onSave(field, draft)}
            >
              <Check className="size-4" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-label={`Discard changes to ${field.label}`}
              onClick={() => setDraft(field.display_value)}
            >
              <X className="size-4" />
            </Button>
          </>
        )}
      </div>

      {field.corrections.length > 0 && (
        <p className="mt-1 text-xs text-text-muted">
          Corrected {field.corrections.length} time{field.corrections.length === 1 ? '' : 's'} — last by{' '}
          {field.corrections[0]?.corrected_by_email ?? 'unknown'}
        </p>
      )}
    </div>
  );
}

import { forwardRef, type ReactNode } from 'react';
import * as RadixSelect from '@radix-ui/react-select';
import { Check, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps {
  options: SelectOption[];
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  placeholder?: string;
  'aria-label'?: string;
  disabled?: boolean;
  className?: string;
}

/** Thin wrapper over Radix Select — gets keyboard navigation, typeahead,
 * and correct ARIA roles for free instead of hand-rolling a listbox. */
export const Select = forwardRef<HTMLButtonElement, SelectProps>(
  ({ options, value, defaultValue, onValueChange, placeholder, disabled, className, ...aria }, ref) => {
    return (
      <RadixSelect.Root value={value} defaultValue={defaultValue} onValueChange={onValueChange} disabled={disabled}>
        <RadixSelect.Trigger
          ref={ref}
          className={cn(
            'flex h-10 w-full items-center justify-between rounded-md border border-border bg-card px-3 text-sm text-text-primary',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
            'disabled:cursor-not-allowed disabled:opacity-50 data-[placeholder]:text-text-muted',
            className,
          )}
          {...aria}
        >
          <RadixSelect.Value placeholder={placeholder} />
          <RadixSelect.Icon>
            <ChevronDown className="h-4 w-4 text-text-muted" aria-hidden="true" />
          </RadixSelect.Icon>
        </RadixSelect.Trigger>
        <RadixSelect.Portal>
          <RadixSelect.Content
            className="z-dropdown overflow-hidden rounded-md border border-border bg-card shadow-md"
            position="popper"
            sideOffset={4}
          >
            <RadixSelect.Viewport className="p-1">
              {options.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </RadixSelect.Viewport>
          </RadixSelect.Content>
        </RadixSelect.Portal>
      </RadixSelect.Root>
    );
  },
);
Select.displayName = 'Select';

function SelectItem({ value, children }: { value: string; children: ReactNode }) {
  return (
    <RadixSelect.Item
      value={value}
      className={cn(
        'relative flex h-9 cursor-pointer select-none items-center rounded-sm px-8 text-sm text-text-primary',
        'data-[highlighted]:bg-primary-soft data-[highlighted]:outline-none',
      )}
    >
      <RadixSelect.ItemIndicator className="absolute left-2 inline-flex items-center">
        <Check className="h-4 w-4 text-primary" aria-hidden="true" />
      </RadixSelect.ItemIndicator>
      <RadixSelect.ItemText>{children}</RadixSelect.ItemText>
    </RadixSelect.Item>
  );
}

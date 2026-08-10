import { useState, type DragEvent } from 'react';
import { UploadCloud } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface UploadDropzoneProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

const ALLOWED_EXTENSIONS = '.pdf, .png, .jpg, .jpeg, .docx, .xlsx, .csv, .txt';

/**
 * Wraps a real (visually-hidden but focusable) file input in a `<label>`
 * rather than a custom `role="button"` div — this gets native
 * click-to-open, Tab-to-focus, and Enter/Space-to-open-picker behavior
 * for free instead of re-implementing it with ARIA and key handlers.
 * Drag-and-drop is layered on top via the wrapping element's own drag
 * events, which fire regardless of the label/input relationship.
 */
export function UploadDropzone({ onFilesSelected, disabled = false }: UploadDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    onFilesSelected(Array.from(fileList));
  };

  const handleDragOver = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setIsDragging(false);
    if (!disabled) handleFiles(event.dataTransfer.files);
  };

  return (
    <label
      htmlFor="document-upload-input"
      onDragOver={handleDragOver}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={cn(
        'flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors duration-fast',
        disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
        isDragging ? 'border-primary bg-primary-soft' : 'border-border bg-lavender/40',
      )}
    >
      <UploadCloud className="h-8 w-8 text-primary" aria-hidden="true" />
      <span className="text-sm font-medium text-text-primary">Drag and drop files here, or click to browse</span>
      <span className="text-xs text-text-muted">{ALLOWED_EXTENSIONS} — up to 20MB</span>
      <input
        id="document-upload-input"
        type="file"
        multiple
        disabled={disabled}
        className="sr-only"
        onChange={(event) => {
          handleFiles(event.target.files);
          event.target.value = '';
        }}
      />
    </label>
  );
}

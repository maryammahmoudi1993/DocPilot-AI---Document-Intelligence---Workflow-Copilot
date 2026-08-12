import { useEffect, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, RotateCw, ZoomIn, ZoomOut } from 'lucide-react';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import { IconButton } from '@/components/ui/IconButton';
import type { BoundingBox } from '@/features/extraction/types';

// pdfjs-dist needs an explicit worker URL under Vite — resolved at build
// time so it's bundled/served correctly in both dev and prod, rather
// than relying on a CDN (keeps document content off any third party).
async function loadPdfjs() {
  const pdfjsLib = await import('pdfjs-dist');
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.mjs', import.meta.url).toString();
  return pdfjsLib;
}

export interface PDFViewerProps {
  fileUrl: string;
  /** Page + normalized (0..1) box to highlight — set when the selected
   * extraction field carries source coordinates. Absent for fields the
   * provider didn't localize; the viewer works fine without it. */
  highlight?: { page: number; box: BoundingBox } | null;
}

const MIN_SCALE = 0.5;
const MAX_SCALE = 2.5;

export function PDFViewer({ fileUrl, highlight }: PDFViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [pdfDoc, setPdfDoc] = useState<PDFDocumentProxy | null>(null);
  const [pageCount, setPageCount] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [overlayStyle, setOverlayStyle] = useState<React.CSSProperties | null>(null);

  // Read (not reactively depended on) from the load effect below, so a
  // highlight already selected when a new document starts loading is
  // honored without making every highlight change re-fetch the document.
  const highlightRef = useRef(highlight);
  useEffect(() => {
    highlightRef.current = highlight;
  }, [highlight]);

  useEffect(() => {
    let cancelled = false;
    loadPdfjs()
      .then((pdfjsLib) => pdfjsLib.getDocument({ url: fileUrl }).promise)
      .then((doc) => {
        if (cancelled) return;
        setError(null);
        setPdfDoc(doc);
        setPageCount(doc.numPages);
        // Land on the highlighted field's page if one was already
        // selected when this document started loading, rather than
        // always resetting to page 1 and stomping it.
        setPageNumber(highlightRef.current?.page ?? 1);
      })
      .catch(() => {
        if (!cancelled) setError('The document preview could not be loaded.');
      });
    return () => {
      cancelled = true;
    };
  }, [fileUrl]);

  // Jumps to the highlighted field's page whenever the selection changes
  // — adjusted during render (React's documented pattern for deriving
  // state from a changed prop) rather than in an effect, so the page
  // updates in the same commit as the selection instead of one tick later.
  const highlightKey = highlight ? `${highlight.page}:${highlight.box.x}:${highlight.box.y}` : null;
  const [lastHighlightKey, setLastHighlightKey] = useState<string | null>(null);
  if (highlightKey !== lastHighlightKey) {
    setLastHighlightKey(highlightKey);
    if (highlight) setPageNumber(highlight.page);
  }

  useEffect(() => {
    if (!pdfDoc || !canvasRef.current) return;
    let cancelled = false;

    pdfDoc.getPage(pageNumber).then(async (page) => {
      if (cancelled) return;
      const viewport = page.getViewport({ scale, rotation });
      const canvas = canvasRef.current;
      if (!canvas) return;
      const context = canvas.getContext('2d');
      if (!context) return;
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      await page.render({ canvasContext: context, viewport, canvas }).promise;
      if (cancelled) return;

      if (highlight && highlight.page === pageNumber) {
        setOverlayStyle({
          position: 'absolute',
          left: `${highlight.box.x * viewport.width}px`,
          top: `${highlight.box.y * viewport.height}px`,
          width: `${highlight.box.width * viewport.width}px`,
          height: `${highlight.box.height * viewport.height}px`,
        });
      } else {
        setOverlayStyle(null);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [pdfDoc, pageNumber, scale, rotation, highlight]);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-border bg-lavender p-6 text-sm text-text-secondary">
        {error}
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="mb-2 flex items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 py-2">
        <div className="flex items-center gap-1">
          <IconButton
            aria-label="Previous page"
            disabled={pageNumber <= 1}
            onClick={() => setPageNumber((n) => Math.max(1, n - 1))}
          >
            <ChevronLeft className="size-4" />
          </IconButton>
          <span className="min-w-16 text-center text-sm text-text-secondary">
            {pageCount === 0 ? '—' : `${pageNumber} / ${pageCount}`}
          </span>
          <IconButton
            aria-label="Next page"
            disabled={pageNumber >= pageCount}
            onClick={() => setPageNumber((n) => Math.min(pageCount, n + 1))}
          >
            <ChevronRight className="size-4" />
          </IconButton>
        </div>
        <div className="flex items-center gap-1">
          <IconButton aria-label="Zoom out" disabled={scale <= MIN_SCALE} onClick={() => setScale((s) => Math.max(MIN_SCALE, s - 0.25))}>
            <ZoomOut className="size-4" />
          </IconButton>
          <span className="min-w-12 text-center text-sm text-text-secondary">{Math.round(scale * 100)}%</span>
          <IconButton aria-label="Zoom in" disabled={scale >= MAX_SCALE} onClick={() => setScale((s) => Math.min(MAX_SCALE, s + 0.25))}>
            <ZoomIn className="size-4" />
          </IconButton>
          <IconButton aria-label="Rotate page" onClick={() => setRotation((r) => (r + 90) % 360)}>
            <RotateCw className="size-4" />
          </IconButton>
        </div>
      </div>

      <div className="relative flex-1 overflow-auto rounded-lg border border-border bg-page p-4">
        <div className="relative mx-auto w-fit">
          <canvas ref={canvasRef} data-testid="pdf-canvas" />
          {overlayStyle && (
            <div
              data-testid="pdf-highlight"
              style={overlayStyle}
              className="pointer-events-none rounded-sm border-2 border-primary bg-primary/20"
            />
          )}
        </div>
      </div>
    </div>
  );
}

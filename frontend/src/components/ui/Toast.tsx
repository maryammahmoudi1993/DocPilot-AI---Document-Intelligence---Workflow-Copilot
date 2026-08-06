import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import * as RadixToast from '@radix-ui/react-toast';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export type ToastVariant = 'success' | 'error' | 'info';

interface ToastMessage {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  showToast: (toast: Omit<ToastMessage, 'id'>) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const VARIANT_ICON: Record<ToastVariant, typeof CheckCircle2> = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
};

const VARIANT_CLASSES: Record<ToastVariant, string> = {
  success: 'border-status-approved/30 bg-status-approved-bg text-text-primary',
  error: 'border-status-failed/30 bg-status-failed-bg text-text-primary',
  info: 'border-border bg-card text-text-primary',
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = useCallback((toast: Omit<ToastMessage, 'id'>) => {
    const id = crypto.randomUUID();
    setToasts((current) => [...current, { ...toast, id }]);
  }, []);

  const dismiss = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const value = useMemo(() => ({ showToast }), [showToast]);

  return (
    <ToastContext.Provider value={value}>
      <RadixToast.Provider swipeDirection="right">
        {children}
        {toasts.map((toast) => {
          const Icon = VARIANT_ICON[toast.variant];
          return (
            <RadixToast.Root
              key={toast.id}
              duration={5000}
              onOpenChange={(open) => !open && dismiss(toast.id)}
              className={cn(
                'flex items-start gap-3 rounded-md border p-4 shadow-md',
                VARIANT_CLASSES[toast.variant],
              )}
            >
              <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
              <div className="flex-1">
                <RadixToast.Title className="text-sm font-semibold">{toast.title}</RadixToast.Title>
                {toast.description && (
                  <RadixToast.Description className="mt-1 text-sm text-text-secondary">
                    {toast.description}
                  </RadixToast.Description>
                )}
              </div>
              <RadixToast.Close aria-label="Dismiss notification" className="text-text-muted hover:text-text-primary">
                <X className="h-4 w-4" aria-hidden="true" />
              </RadixToast.Close>
            </RadixToast.Root>
          );
        })}
        <RadixToast.Viewport className="fixed bottom-0 right-0 z-toast m-0 flex w-96 max-w-[100vw] list-none flex-col gap-2 p-6 outline-none" />
      </RadixToast.Provider>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

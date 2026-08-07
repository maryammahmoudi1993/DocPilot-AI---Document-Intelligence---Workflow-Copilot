import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useLocation, useNavigate, type Location } from 'react-router-dom';
import { Sparkles, FileStack } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useLogin } from '@/features/auth/hooks';
import { ApiError } from '@/lib/apiClient';

const signInSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

type SignInFormValues = z.infer<typeof signInSchema>;

interface LocationState {
  from?: Location;
}

/** Matches design-reference/ui/DocPilot AI - Sign In.dc.html (two-column
 * brand + form layout, same token language) — reimplemented as real
 * components, not the reference markup itself. The reference's
 * "Remember me" checkbox and "Forgot password?" link aren't wired to
 * any real behavior on the backend yet, so they're omitted rather than
 * shipped as non-functional controls. */
export function SignInPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const login = useLogin();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignInFormValues>({ resolver: zodResolver(signInSchema) });

  const onSubmit = (values: SignInFormValues) => {
    setFormError(null);
    login.mutate(values, {
      onSuccess: () => {
        const from = (location.state as LocationState | null)?.from?.pathname ?? '/app/dashboard';
        navigate(from, { replace: true });
      },
      onError: (error) => {
        if (error instanceof ApiError && error.code === 'throttled') {
          setFormError('Too many attempts. Please wait a moment and try again.');
        } else if (error instanceof ApiError && error.code === 'authentication_failed') {
          setFormError('Invalid email or password.');
        } else {
          setFormError('Something went wrong. Please try again.');
        }
      },
    });
  };

  return (
    <div className="grid min-h-screen grid-cols-1 md:grid-cols-2">
      <div className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-primary to-[#5B47D8] p-12 text-white md:flex">
        <div className="relative z-10 flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-white/20">
            <FileStack className="h-4 w-4 text-white" aria-hidden="true" />
          </div>
          <span className="text-lg font-extrabold tracking-tight">DocPilot AI</span>
        </div>

        <div className="relative z-10">
          <h1 className="mb-3.5 text-3xl font-extrabold leading-tight tracking-tight">
            Turn documents into structured data, trusted answers, and automated actions.
          </h1>
          <p className="max-w-md text-sm text-[#DED6FC]">
            Extraction, review, citations, and automation — all in one connected workspace.
          </p>

          <div className="mt-9 max-w-md rounded-2xl border border-white/15 bg-white/10 p-5">
            <div className="mb-2.5 flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-[#FFD166]" aria-hidden="true" />
              <span className="text-xs font-bold">AI Assistant</span>
            </div>
            <p className="text-sm text-[#F5F2FF]">Example: "3 contracts expire within 60 days."</p>
            <p className="mt-1.5 text-xs text-[#C9BCF7]">Illustrative — sample workspace data.</p>
          </div>
        </div>

        <div className="relative z-10 text-xs text-[#C9BCF7]">Portfolio demonstration</div>

        <div
          className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-white/5"
          aria-hidden="true"
        />
        <div
          className="absolute -bottom-16 -left-16 h-56 w-56 rounded-full bg-white/5"
          aria-hidden="true"
        />
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">
          <h2 className="text-2xl font-bold text-text-primary">Welcome back</h2>
          <p className="mb-7 mt-1 text-sm text-text-secondary">Sign in to your DocPilot AI workspace.</p>

          <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
            <div>
              <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-text-primary">
                Email
              </label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="alex@company.com"
                hasError={!!errors.email}
                aria-describedby={errors.email ? 'email-error' : undefined}
                {...register('email')}
              />
              {errors.email && (
                <p id="email-error" role="alert" className="mt-1 text-xs text-status-failed">
                  {errors.email.message}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-text-primary">
                Password
              </label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                hasError={!!errors.password}
                aria-describedby={errors.password ? 'password-error' : undefined}
                {...register('password')}
              />
              {errors.password && (
                <p id="password-error" role="alert" className="mt-1 text-xs text-status-failed">
                  {errors.password.message}
                </p>
              )}
            </div>

            {formError && (
              <p role="alert" className="text-sm text-status-failed">
                {formError}
              </p>
            )}

            <Button type="submit" className="w-full" isLoading={login.isPending}>
              Sign In
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}

'use client';

import { useState, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth.store';
import { Loader2, LogIn, Bot } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const login = useAuthStore((s) => s.login);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [tenantSlug, setTenantSlug] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Simple validation
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  function validate(): boolean {
    const errors: Record<string, string> = {};

    if (!email.trim()) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = 'Enter a valid email address';
    }

    if (!password.trim()) {
      errors.password = 'Password is required';
    } else if (password.length < 6) {
      errors.password = 'Password must be at least 6 characters';
    }

    if (!tenantSlug.trim()) {
      errors.tenantSlug = 'Workspace slug is required';
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');

    if (!validate()) return;

    setIsSubmitting(true);
    try {
      await login(email.trim(), password, tenantSlug.trim().toLowerCase());
      router.push('/dashboard');
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { message?: string }; status?: number } };
      if (axiosError.response?.status === 401) {
        setError('Invalid email or password. Please try again.');
      } else if (axiosError.response?.data?.message) {
        setError(axiosError.response.data.message);
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="w-full max-w-md">
      {/* Logo / Branding */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-primary-600 text-white mb-4">
          <Bot className="w-8 h-8" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Sign in to your workspace</h1>
        <p className="text-sm text-gray-500 mt-1">AISA — AI Digital Workforce Platform</p>
      </div>

      {/* Card */}
      <div className="bg-white rounded-2xl shadow-xl shadow-gray-200/60 border border-gray-100 p-8">
        {/* Global error */}
        {error && (
          <div className="mb-5 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {/* Workspace slug */}
          <div>
            <label htmlFor="tenantSlug" className="block text-sm font-medium text-gray-700 mb-1.5">
              Workspace
            </label>
            <div className="relative">
              <input
                id="tenantSlug"
                type="text"
                value={tenantSlug}
                onChange={(e) => {
                  setTenantSlug(e.target.value);
                  setFieldErrors((prev) => ({ ...prev, tenantSlug: '' }));
                }}
                placeholder="your-company"
                autoComplete="organization"
                className={`
                  w-full rounded-lg border px-3.5 py-2.5 text-sm text-gray-900
                  placeholder:text-gray-400 outline-none transition-colors
                  focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20
                  ${fieldErrors.tenantSlug ? 'border-red-300 bg-red-50/50' : 'border-gray-300 bg-white'}
                `}
              />
            </div>
            {fieldErrors.tenantSlug && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.tenantSlug}</p>
            )}
          </div>

          {/* Email */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1.5">
              Email address
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setFieldErrors((prev) => ({ ...prev, email: '' }));
              }}
              placeholder="you@example.com"
              autoComplete="email"
              className={`
                w-full rounded-lg border px-3.5 py-2.5 text-sm text-gray-900
                placeholder:text-gray-400 outline-none transition-colors
                focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20
                ${fieldErrors.email ? 'border-red-300 bg-red-50/50' : 'border-gray-300 bg-white'}
              `}
            />
            {fieldErrors.email && <p className="mt-1 text-xs text-red-600">{fieldErrors.email}</p>}
          </div>

          {/* Password */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1.5">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setFieldErrors((prev) => ({ ...prev, password: '' }));
              }}
              placeholder="Enter your password"
              autoComplete="current-password"
              className={`
                w-full rounded-lg border px-3.5 py-2.5 text-sm text-gray-900
                placeholder:text-gray-400 outline-none transition-colors
                focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20
                ${fieldErrors.password ? 'border-red-300 bg-red-50/50' : 'border-gray-300 bg-white'}
              `}
            />
            {fieldErrors.password && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.password}</p>
            )}
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="
              w-full flex items-center justify-center gap-2 rounded-lg
              bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white
              hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500/50
              disabled:opacity-60 disabled:cursor-not-allowed transition-colors
            "
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Signing in...
              </>
            ) : (
              <>
                <LogIn className="w-4 h-4" />
                Sign in
              </>
            )}
          </button>
        </form>
      </div>

      {/* Footer */}
      <p className="text-center text-xs text-gray-400 mt-6">
        AISA &mdash; AI Digital Workforce Platform
      </p>
    </div>
  );
}

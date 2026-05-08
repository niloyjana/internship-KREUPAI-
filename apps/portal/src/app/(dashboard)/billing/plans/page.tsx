'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Check,
  X as XIcon,
  Crown,
  Zap,
  Building2,
  Sparkles,
  ArrowRight,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

/* ------------------------------------------------------------------ */
/*  Sub-navigation                                                      */
/* ------------------------------------------------------------------ */

const billingTabs = [
  { label: 'Overview', href: '/billing' },
  { label: 'Invoices', href: '/billing/invoices' },
  { label: 'Usage', href: '/billing/usage' },
  { label: 'Plans', href: '/billing/plans' },
];

/* ------------------------------------------------------------------ */
/*  Plan Data                                                           */
/* ------------------------------------------------------------------ */

interface Plan {
  id: string;
  name: string;
  description: string;
  price: number;
  priceLabel: string;
  icon: React.ElementType;
  popular?: boolean;
  features: { label: string; included: boolean }[];
  ctaLabel: string;
  ctaVariant: 'primary' | 'outline' | 'disabled';
}

const CURRENT_PLAN = 'professional';

const PLANS: Plan[] = [
  {
    id: 'starter',
    name: 'Starter',
    description: 'For small teams getting started with AI agents.',
    price: 49,
    priceLabel: '/month',
    icon: Zap,
    features: [
      { label: 'Up to 3 AI agents', included: true },
      { label: '5,000 tasks/month', included: true },
      { label: 'Email support', included: true },
      { label: 'Basic analytics', included: true },
      { label: 'Custom integrations', included: false },
      { label: 'SSO / SAML', included: false },
      { label: 'Audit logs', included: false },
      { label: 'Dedicated account manager', included: false },
      { label: 'SLA guarantee', included: false },
    ],
    ctaLabel: 'Downgrade',
    ctaVariant: 'outline',
  },
  {
    id: 'professional',
    name: 'Professional',
    description: 'For growing teams that need more power and flexibility.',
    price: 199,
    priceLabel: '/month',
    icon: Crown,
    popular: true,
    features: [
      { label: 'Up to 15 AI agents', included: true },
      { label: '50,000 tasks/month', included: true },
      { label: 'Priority email & chat support', included: true },
      { label: 'Advanced analytics & dashboards', included: true },
      { label: 'Custom integrations', included: true },
      { label: 'SSO / SAML', included: true },
      { label: 'Audit logs', included: true },
      { label: 'Dedicated account manager', included: false },
      { label: 'SLA guarantee', included: false },
    ],
    ctaLabel: 'Current Plan',
    ctaVariant: 'disabled',
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    description: 'For organizations that need full control and dedicated support.',
    price: 0,
    priceLabel: 'Custom pricing',
    icon: Building2,
    features: [
      { label: 'Unlimited AI agents', included: true },
      { label: 'Unlimited tasks', included: true },
      { label: '24/7 phone & Slack support', included: true },
      { label: 'Custom analytics & reporting', included: true },
      { label: 'Custom integrations', included: true },
      { label: 'SSO / SAML', included: true },
      { label: 'Audit logs with retention', included: true },
      { label: 'Dedicated account manager', included: true },
      { label: '99.9% SLA guarantee', included: true },
    ],
    ctaLabel: 'Contact Sales',
    ctaVariant: 'primary',
  },
];

/* ------------------------------------------------------------------ */
/*  Page Component                                                     */
/* ------------------------------------------------------------------ */

export default function BillingPlansPage() {
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);

  async function handlePlanAction(planId: string) {
    if (planId === CURRENT_PLAN) return;
    setLoadingPlan(planId);
    // Simulate API call
    await new Promise((r) => setTimeout(r, 1000));
    setLoadingPlan(null);
    // In production, this would redirect to Stripe or show a confirmation
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Billing</h1>
        <p className="text-sm text-gray-500 mt-1">
          Choose the plan that fits your team. Upgrade or downgrade anytime.
        </p>
      </div>

      {/* Sub-navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-6">
          {billingTabs.map((tab) => (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                'pb-3 text-sm font-medium border-b-2 transition-colors',
                tab.href === '/billing/plans'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              )}
            >
              {tab.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Current Plan Banner */}
      <div className="flex items-center gap-3 p-4 rounded-lg bg-primary-50 border border-primary-200">
        <Sparkles className="w-5 h-5 text-primary-600 flex-shrink-0" />
        <div>
          <p className="text-sm font-medium text-primary-800">
            You are currently on the <strong>Professional</strong> plan.
          </p>
          <p className="text-xs text-primary-600 mt-0.5">
            Your next billing date is April 1, 2026.
          </p>
        </div>
      </div>

      {/* Plan Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {PLANS.map((plan) => {
          const isCurrent = plan.id === CURRENT_PLAN;
          const isLoading = loadingPlan === plan.id;

          return (
            <div
              key={plan.id}
              className={cn(
                'relative bg-white rounded-xl border shadow-sm flex flex-col',
                isCurrent
                  ? 'border-primary-300 ring-2 ring-primary-100'
                  : 'border-gray-200',
              )}
            >
              {/* Popular badge */}
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-primary-600 text-white text-xs font-medium shadow-sm">
                    <Sparkles className="w-3 h-3" />
                    Current Plan
                  </span>
                </div>
              )}

              {/* Plan Header */}
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-center gap-3 mb-3">
                  <div
                    className={cn(
                      'flex items-center justify-center w-10 h-10 rounded-lg',
                      isCurrent ? 'bg-primary-50 text-primary-600' : 'bg-gray-100 text-gray-600',
                    )}
                  >
                    <plan.icon className="w-5 h-5" />
                  </div>
                  <h3 className="text-lg font-bold text-gray-900">{plan.name}</h3>
                </div>
                <p className="text-sm text-gray-500">{plan.description}</p>
                <div className="mt-4">
                  {plan.price > 0 ? (
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl font-bold text-gray-900">${plan.price}</span>
                      <span className="text-sm text-gray-500">{plan.priceLabel}</span>
                    </div>
                  ) : (
                    <p className="text-lg font-semibold text-gray-900">{plan.priceLabel}</p>
                  )}
                </div>
              </div>

              {/* Features */}
              <div className="p-6 flex-1">
                <ul className="space-y-3">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start gap-2.5">
                      {feature.included ? (
                        <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                      ) : (
                        <XIcon className="w-4 h-4 text-gray-300 mt-0.5 flex-shrink-0" />
                      )}
                      <span
                        className={cn(
                          'text-sm',
                          feature.included ? 'text-gray-700' : 'text-gray-400',
                        )}
                      >
                        {feature.label}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* CTA */}
              <div className="p-6 pt-0">
                <button
                  onClick={() => handlePlanAction(plan.id)}
                  disabled={isCurrent || isLoading}
                  className={cn(
                    'w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    plan.ctaVariant === 'primary' &&
                      'bg-primary-600 text-white hover:bg-primary-700',
                    plan.ctaVariant === 'outline' &&
                      'border border-gray-300 text-gray-700 hover:bg-gray-50',
                    plan.ctaVariant === 'disabled' &&
                      'bg-gray-100 text-gray-500 cursor-not-allowed',
                    (isCurrent || isLoading) && 'opacity-60 cursor-not-allowed',
                  )}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      {plan.ctaLabel}
                      {!isCurrent && <ArrowRight className="w-4 h-4" />}
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Feature Comparison Table */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="p-6 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Feature Comparison</h2>
          <p className="text-sm text-gray-500 mt-1">
            Detailed comparison of what each plan includes.
          </p>
        </div>
        <div className="p-6">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-3 pr-4 font-medium text-gray-500 w-1/3">Feature</th>
                  <th className="text-center py-3 px-4 font-medium text-gray-500">Starter</th>
                  <th className="text-center py-3 px-4 font-medium text-primary-600">
                    Professional
                  </th>
                  <th className="text-center py-3 pl-4 font-medium text-gray-500">Enterprise</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { feature: 'AI Agents', starter: 'Up to 3', professional: 'Up to 15', enterprise: 'Unlimited' },
                  { feature: 'Monthly Tasks', starter: '5,000', professional: '50,000', enterprise: 'Unlimited' },
                  { feature: 'Analytics', starter: 'Basic', professional: 'Advanced', enterprise: 'Custom' },
                  { feature: 'Support', starter: 'Email', professional: 'Email & Chat', enterprise: '24/7 Phone & Slack' },
                  { feature: 'Custom Integrations', starter: false, professional: true, enterprise: true },
                  { feature: 'SSO / SAML', starter: false, professional: true, enterprise: true },
                  { feature: 'Audit Logs', starter: false, professional: true, enterprise: true },
                  { feature: 'Dedicated Manager', starter: false, professional: false, enterprise: true },
                  { feature: 'SLA Guarantee', starter: false, professional: false, enterprise: '99.9%' },
                  { feature: 'Data Retention', starter: '30 days', professional: '90 days', enterprise: 'Custom' },
                ].map((row, idx) => (
                  <tr key={idx} className="border-b border-gray-50 last:border-0">
                    <td className="py-3 pr-4 font-medium text-gray-700">{row.feature}</td>
                    {(['starter', 'professional', 'enterprise'] as const).map((plan) => {
                      const val = row[plan];
                      return (
                        <td
                          key={plan}
                          className={cn(
                            'py-3 px-4 text-center',
                            plan === 'professional' && 'bg-primary-50/30',
                          )}
                        >
                          {typeof val === 'boolean' ? (
                            val ? (
                              <Check className="w-4 h-4 text-green-500 mx-auto" />
                            ) : (
                              <XIcon className="w-4 h-4 text-gray-300 mx-auto" />
                            )
                          ) : (
                            <span className="text-sm text-gray-600">{val}</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

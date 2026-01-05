"use client"

import Link from "next/link"
import { Check, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth/auth-context"

interface PricingTier {
  name: string
  price: string
  period: string
  description: string
  features: string[]
  cta: string
  href: string
  popular?: boolean
}

const PRICING_TIERS: PricingTier[] = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Perfect for getting started with stock research.",
    features: [
      "Up to 10 stocks in watchlist",
      "Real-time quotes",
      "Basic stock details",
      "Market news feed",
      "Search all US exchanges",
    ],
    cta: "Get Started",
    href: "/signup",
  },
  {
    name: "Pro",
    price: "$19",
    period: "per month",
    description: "Advanced features for serious investors.",
    features: [
      "Unlimited watchlist",
      "Real-time quotes",
      "Extended company data",
      "Personalized news feed",
      "Price alerts via email",
      "Historical data access",
      "Priority support",
    ],
    cta: "Start Free Trial",
    href: "/signup",
    popular: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "per month",
    description: "For teams and organizations with custom needs.",
    features: [
      "Everything in Pro",
      "API access",
      "Custom integrations",
      "Dedicated account manager",
      "SLA guarantee",
      "Team collaboration",
      "Custom data feeds",
    ],
    cta: "Contact Sales",
    href: "/about",
  },
]

export default function PricingContent() {
  const { isAuthenticated } = useAuth()

  return (
    <main className="flex-1 pt-14">
      {/* Hero Section */}
      <section className="bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-20 text-center">
          <h1 className="text-4xl md:text-5xl font-semibold text-gray-900 mb-4">
            Simple, transparent pricing
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Choose the plan that fits your research needs. Upgrade or downgrade at any time.
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="max-w-6xl mx-auto px-6 md:px-8 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {PRICING_TIERS.map((tier) => (
            <div
              key={tier.name}
              className={cn(
                "relative rounded-2xl border p-8 flex flex-col",
                tier.popular
                  ? "border-gray-900 bg-gray-900 text-white shadow-xl"
                  : "border-gray-200 bg-white"
              )}
            >
              {tier.popular && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                  <span className="inline-flex items-center gap-1 px-4 py-1 rounded-full bg-white text-gray-900 text-sm font-medium shadow-sm">
                    <Sparkles className="w-4 h-4" />
                    Most Popular
                  </span>
                </div>
              )}

              <div className="mb-6">
                <h3
                  className={cn(
                    "text-lg font-semibold mb-2",
                    tier.popular ? "text-white" : "text-gray-900"
                  )}
                >
                  {tier.name}
                </h3>
                <div className="flex items-baseline gap-1">
                  <span
                    className={cn(
                      "text-4xl font-semibold",
                      tier.popular ? "text-white" : "text-gray-900"
                    )}
                  >
                    {tier.price}
                  </span>
                  <span
                    className={cn(
                      "text-sm",
                      tier.popular ? "text-gray-300" : "text-gray-500"
                    )}
                  >
                    /{tier.period}
                  </span>
                </div>
                <p
                  className={cn(
                    "mt-3 text-sm",
                    tier.popular ? "text-gray-300" : "text-gray-600"
                  )}
                >
                  {tier.description}
                </p>
              </div>

              <ul className="space-y-3 mb-8 flex-1">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-3">
                    <Check
                      className={cn(
                        "w-5 h-5 shrink-0 mt-0.5",
                        tier.popular ? "text-green-400" : "text-green-600"
                      )}
                    />
                    <span
                      className={cn(
                        "text-sm",
                        tier.popular ? "text-gray-200" : "text-gray-600"
                      )}
                    >
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>

              <Link href={isAuthenticated ? "/settings?tab=billing" : tier.href}>
                <Button
                  className={cn(
                    "w-full",
                    tier.popular
                      ? "bg-white text-gray-900 hover:bg-gray-100"
                      : "bg-gray-900 text-white hover:bg-gray-800"
                  )}
                >
                  {isAuthenticated && tier.name !== "Enterprise"
                    ? "Upgrade"
                    : tier.cta}
                </Button>
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ Section */}
      <section className="bg-gray-50 border-t border-gray-100">
        <div className="max-w-3xl mx-auto px-6 md:px-8 py-20">
          <h2 className="text-2xl font-semibold text-gray-900 mb-8 text-center">
            Frequently asked questions
          </h2>
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-gray-100 p-6">
              <h3 className="font-semibold text-gray-900 mb-2">
                Can I cancel my subscription at any time?
              </h3>
              <p className="text-gray-600 text-sm">
                Yes, you can cancel your subscription at any time. Your access will continue until the end of your current billing period.
              </p>
            </div>
            <div className="bg-white rounded-xl border border-gray-100 p-6">
              <h3 className="font-semibold text-gray-900 mb-2">
                What payment methods do you accept?
              </h3>
              <p className="text-gray-600 text-sm">
                We accept all major credit cards including Visa, Mastercard, and American Express. We also support payment via PayPal.
              </p>
            </div>
            <div className="bg-white rounded-xl border border-gray-100 p-6">
              <h3 className="font-semibold text-gray-900 mb-2">
                Is there a free trial for Pro?
              </h3>
              <p className="text-gray-600 text-sm">
                Yes, all new Pro subscriptions come with a 14-day free trial. You will not be charged until the trial ends.
              </p>
            </div>
            <div className="bg-white rounded-xl border border-gray-100 p-6">
              <h3 className="font-semibold text-gray-900 mb-2">
                What is included in API access?
              </h3>
              <p className="text-gray-600 text-sm">
                Enterprise plans include full API access for programmatic data retrieval, including real-time quotes, historical data, and company information.
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}

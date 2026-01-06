'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { format } from 'date-fns'
import Header from '@/components/header'
import Sidebar from '@/components/sidebar'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Mail, Calendar, Shield, CreditCard, Clock } from 'lucide-react'
import { useAuth } from '@/lib/auth/auth-context'
import Link from 'next/link'

const getInitials = (name?: string, email?: string): string => {
  if (name && name.trim()) {
    const parts = name.trim().split(' ')
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    }
    return name.slice(0, 2).toUpperCase()
  }
  if (email) {
    return email.slice(0, 2).toUpperCase()
  }
  return 'U'
}

const formatDate = (dateString?: string): string => {
  if (!dateString) return 'Unknown'
  try {
    return format(new Date(dateString), 'MMM d, yyyy')
  } catch {
    return 'Unknown'
  }
}

const getTierBadgeVariant = (
  tier: string,
): 'default' | 'secondary' | 'destructive' | 'outline' => {
  switch (tier.toLowerCase()) {
    case 'pro':
    case 'premium':
      return 'default'
    case 'enterprise':
      return 'secondary'
    case 'expired':
      return 'destructive'
    default:
      return 'outline'
  }
}

const getTierDisplayName = (tier: string): string => {
  const tierMap: Record<string, string> = {
    free: 'Free',
    pro: 'Pro',
    premium: 'Premium',
    enterprise: 'Enterprise',
  }
  return tierMap[tier.toLowerCase()] || tier
}

const ProfileSkeleton = () => (
  <div className="min-h-screen bg-white">
    <Header />
    <Sidebar />
    <main className="md:pl-64 pt-14">
      <div className="max-w-5xl mx-auto px-4 md:px-12 py-8 md:py-12">
        <div className="mb-8 md:mb-12">
          <div className="flex flex-col md:flex-row items-center md:items-start gap-6 md:gap-8">
            <Skeleton className="w-24 h-24 md:w-32 md:h-32 rounded-full" />
            <div className="flex-1 text-center md:text-left">
              <Skeleton className="h-8 md:h-10 w-48 md:w-64 mb-2 mx-auto md:mx-0" />
              <Skeleton className="h-5 md:h-6 w-40 md:w-48 mb-4 md:mb-6 mx-auto md:mx-0" />
              <div className="flex flex-col md:flex-row items-center gap-3 md:gap-6">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-4 w-32" />
              </div>
            </div>
            <Skeleton className="h-10 w-28" />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6 mb-8 md:mb-12">
          <Skeleton className="h-28 md:h-32 rounded-lg" />
          <Skeleton className="h-28 md:h-32 rounded-lg" />
          <Skeleton className="h-28 md:h-32 rounded-lg" />
        </div>
      </div>
    </main>
  </div>
)

export default function ProfilePage() {
  const router = useRouter()
  const { user, isLoading, isAuthenticated } = useAuth()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isLoading, isAuthenticated, router])

  if (isLoading) {
    return <ProfileSkeleton />
  }

  if (!isAuthenticated || !user) {
    return <ProfileSkeleton />
  }

  const isSubscriptionExpiringSoon = (): boolean => {
    if (!user.subscription_end) return false
    const endDate = new Date(user.subscription_end)
    const now = new Date()
    const daysUntilExpiry = Math.ceil(
      (endDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24),
    )
    return daysUntilExpiry <= 30 && daysUntilExpiry > 0
  }

  const isSubscriptionExpired = (): boolean => {
    if (!user.subscription_end) return false
    return new Date(user.subscription_end) < new Date()
  }

  return (
    <div className="min-h-screen bg-white">
      <Header />
      <Sidebar />

      <main className="md:pl-64 pt-14">
        <div className="max-w-5xl mx-auto px-4 md:px-12 py-8 md:py-12">
          {/* Profile Header */}
          <div className="mb-8 md:mb-12">
            <div className="flex flex-col md:flex-row items-center md:items-start gap-6 md:gap-8">
              <div className="relative">
                <div className="w-24 h-24 md:w-32 md:h-32 rounded-full bg-black flex items-center justify-center">
                  <span className="text-3xl md:text-4xl font-medium text-white">
                    {getInitials(user.full_name, user.email)}
                  </span>
                </div>
              </div>

              <div className="flex-1 text-center md:text-left">
                <div className="flex flex-col md:flex-row items-center gap-2 md:gap-3 mb-2">
                  <h1 className="text-2xl md:text-4xl font-normal text-black">
                    {user.full_name || 'User'}
                  </h1>
                  <Badge variant={getTierBadgeVariant(user.tier)}>
                    {getTierDisplayName(user.tier)}
                  </Badge>
                </div>

                <div className="flex flex-col md:flex-row flex-wrap items-center gap-3 md:gap-6 text-sm text-gray-600 mt-4">
                  <div className="flex items-center gap-2">
                    <Mail className="w-4 h-4" />
                    <span className="truncate max-w-[200px] md:max-w-none">{user.email}</span>
                    {user.email_confirmed_at && (
                      <Shield
                        className="w-3 h-3 text-green-600"
                        aria-label="Email verified"
                      />
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4" />
                    <span>Joined {formatDate(user.created_at)}</span>
                  </div>
                  {user.last_sign_in_at && (
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      <span>Last active {formatDate(user.last_sign_in_at)}</span>
                    </div>
                  )}
                </div>
              </div>

              <Link href="/settings" className="w-full md:w-auto">
                <Button className="w-full md:w-auto bg-black text-white hover:bg-gray-800 px-6 text-sm font-normal min-h-[44px]">
                  Edit profile
                </Button>
              </Link>
            </div>
          </div>

          {/* Subscription Section - Only for paid users */}
          {user.tier !== 'free' && (
            <div className="mb-8 md:mb-12 border border-gray-200 rounded-lg p-4 md:p-6">
              <h2 className="text-lg md:text-xl font-normal text-black mb-4 flex items-center gap-2">
                <CreditCard className="w-5 h-5" />
                Subscription
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
                {user.subscription_start && (
                  <div>
                    <div className="text-sm text-gray-600 mb-1">Started</div>
                    <div className="text-lg text-black">
                      {formatDate(user.subscription_start)}
                    </div>
                  </div>
                )}
                {user.subscription_end && (
                  <div>
                    <div className="text-sm text-gray-600 mb-1">
                      {isSubscriptionExpired() ? 'Expired' : 'Renews'}
                    </div>
                    <div
                      className={`text-lg ${
                        isSubscriptionExpired()
                          ? 'text-red-600'
                          : isSubscriptionExpiringSoon()
                            ? 'text-yellow-600'
                            : 'text-black'
                      }`}
                    >
                      {formatDate(user.subscription_end)}
                      {isSubscriptionExpiringSoon() && (
                        <span className="text-sm text-yellow-600 ml-2">
                          (Expiring soon)
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
              {isSubscriptionExpired() && (
                <div className="mt-4 p-3 bg-red-50 rounded-lg text-sm text-red-700">
                  Your subscription has expired. Please renew to continue
                  accessing premium features.
                </div>
              )}
            </div>
          )}

          {/* Account Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 md:gap-6 mb-8 md:mb-12">
            <div className="border border-gray-200 rounded-lg p-4 md:p-6">
              <div className="text-2xl md:text-3xl font-normal text-black mb-2">
                {user.tier === 'free' ? '3' : 'Unlimited'}
              </div>
              <div className="text-sm text-gray-600">Watchlist Limit</div>
            </div>
            <div className="border border-gray-200 rounded-lg p-4 md:p-6">
              <div className="text-2xl md:text-3xl font-normal text-black mb-2">
                {user.email_confirmed_at ? 'Verified' : 'Pending'}
              </div>
              <div className="text-sm text-gray-600">Email Status</div>
            </div>
            <div className="border border-gray-200 rounded-lg p-4 md:p-6 sm:col-span-2 md:col-span-1">
              <div className="text-2xl md:text-3xl font-normal text-black mb-2">
                {getTierDisplayName(user.tier)}
              </div>
              <div className="text-sm text-gray-600">Account Tier</div>
            </div>
          </div>

          {/* Account Information */}
          <div className="mb-8 md:mb-12">
            <h2 className="text-lg md:text-xl font-normal text-black mb-4 md:mb-6">
              Account Information
            </h2>
            <div className="border border-gray-200 rounded-lg divide-y divide-gray-200">
              <div className="flex flex-col md:flex-row md:items-center justify-between p-4 gap-1">
                <div>
                  <div className="text-sm font-medium text-gray-900">
                    User ID
                  </div>
                  <div className="text-xs md:text-sm text-gray-600 font-mono break-all">
                    {user.id}
                  </div>
                </div>
              </div>
              <div className="flex flex-col md:flex-row md:items-center justify-between p-4 gap-2">
                <div>
                  <div className="text-sm font-medium text-gray-900">Email</div>
                  <div className="text-sm text-gray-600 break-all">{user.email}</div>
                </div>
                <div className="flex items-center gap-2">
                  {user.email_confirmed_at ? (
                    <Badge variant="outline" className="text-green-600">
                      Verified
                    </Badge>
                  ) : (
                    <Badge variant="destructive">Unverified</Badge>
                  )}
                </div>
              </div>
              {user.phone && (
                <div className="flex items-center justify-between p-4">
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      Phone
                    </div>
                    <div className="text-sm text-gray-600">{user.phone}</div>
                  </div>
                </div>
              )}
              <div className="flex items-center justify-between p-4">
                <div>
                  <div className="text-sm font-medium text-gray-900">
                    Account Created
                  </div>
                  <div className="text-sm text-gray-600">
                    {formatDate(user.created_at)}
                  </div>
                </div>
              </div>
              {user.last_sign_in_at && (
                <div className="flex items-center justify-between p-4">
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      Last Sign In
                    </div>
                    <div className="text-sm text-gray-600">
                      {formatDate(user.last_sign_in_at)}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Upgrade CTA for Free Users */}
          {user.tier === 'free' && (
            <div className="border border-gray-200 rounded-lg p-6 md:p-8 text-center">
              <h3 className="text-lg md:text-xl font-normal text-black mb-2">
                Upgrade to Pro
              </h3>
              <p className="text-gray-600 mb-6 text-sm md:text-base">
                Get unlimited watchlists, advanced analytics, and priority
                support.
              </p>
              <Button className="bg-black text-white hover:bg-gray-800 px-8 text-sm font-normal min-h-[44px]">
                View Plans
              </Button>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

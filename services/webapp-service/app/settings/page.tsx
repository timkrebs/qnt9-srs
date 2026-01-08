"use client"

import Header from "@/components/header"
import Sidebar from "@/components/sidebar"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/auth/auth-context"
import { authService } from "@/lib/api/auth"
import { notificationService } from "@/lib/api/notifications"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Loader2, Check, AlertCircle, Eye, EyeOff } from "lucide-react"

type TabId = "general" | "account" | "security" | "notifications"

interface NotificationSettings {
  email_notifications: boolean
  product_updates: boolean
  usage_alerts: boolean
  stock_news: boolean
  marketing_emails: boolean
}

export default function SettingsPage() {
  const { user, isLoading: authLoading, isAuthenticated, logout } = useAuth()
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<TabId>("general")
  
  // Form states
  const [fullName, setFullName] = useState("")
  const [email, setEmail] = useState("")
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  
  // Notification settings
  const [notifications, setNotifications] = useState<NotificationSettings>({
    email_notifications: true,
    product_updates: true,
    usage_alerts: true,
    stock_news: true,
    marketing_emails: false,
  })
  
  // Loading/status states
  const [isSavingProfile, setIsSavingProfile] = useState(false)
  const [isSavingPassword, setIsSavingPassword] = useState(false)
  const [isSavingNotifications, setIsSavingNotifications] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isLoadingNotifications, setIsLoadingNotifications] = useState(false)
  const [profileSuccess, setProfileSuccess] = useState(false)
  const [passwordSuccess, setPasswordSuccess] = useState(false)
  const [notificationsSuccess, setNotificationsSuccess] = useState(false)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [notificationsError, setNotificationsError] = useState<string | null>(null)

  const tabs = [
    { id: "general" as TabId, label: "General" },
    { id: "account" as TabId, label: "Account" },
    { id: "security" as TabId, label: "Security" },
    { id: "notifications" as TabId, label: "Notifications" },
  ]

  // Load notification preferences from API
  useEffect(() => {
    const loadNotificationPreferences = async () => {
      if (user && isAuthenticated) {
        setIsLoadingNotifications(true)
        try {
          const prefs = await notificationService.getPreferences()
          setNotifications(prefs)
        } catch (error) {
          console.error("Failed to load notification preferences:", error)
        } finally {
          setIsLoadingNotifications(false)
        }
      }
    }

    loadNotificationPreferences()
  }, [user, isAuthenticated])

  // Populate form with user data
  useEffect(() => {
    if (user) {
      setFullName(user.full_name || "")
      setEmail(user.email || "")
    }
  }, [user])

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login")
    }
  }, [authLoading, isAuthenticated, router])

  const handleSaveProfile = async () => {
    setIsSavingProfile(true)
    setProfileError(null)
    setProfileSuccess(false)

    try {
      await authService.updateProfile({
        full_name: fullName,
        email: email !== user?.email ? email : undefined,
      })
      setProfileSuccess(true)
      setTimeout(() => setProfileSuccess(false), 3000)
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : "Failed to update profile")
    } finally {
      setIsSavingProfile(false)
    }
  }

  const handleUpdatePassword = async () => {
    setPasswordError(null)
    setPasswordSuccess(false)

    // Validate current password is provided
    if (!currentPassword.trim()) {
      setPasswordError("Current password is required")
      return
    }

    // Validate passwords
    if (newPassword !== confirmPassword) {
      setPasswordError("Passwords do not match")
      return
    }

    if (newPassword.length < 8) {
      setPasswordError("Password must be at least 8 characters")
      return
    }

    setIsSavingPassword(true)

    try {
      await authService.updatePassword(currentPassword, newPassword)
      setPasswordSuccess(true)
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
      setTimeout(() => setPasswordSuccess(false), 3000)
    } catch (error) {
      setPasswordError(error instanceof Error ? error.message : "Failed to update password")
    } finally {
      setIsSavingPassword(false)
    }
  }

  const handleSaveNotifications = async () => {
    setIsSavingNotifications(true)
    setNotificationsSuccess(false)
    setNotificationsError(null)

    try {
      await notificationService.updatePreferences(notifications)
      setNotificationsSuccess(true)
      setTimeout(() => setNotificationsSuccess(false), 3000)
    } catch (error) {
      setNotificationsError(error instanceof Error ? error.message : "Failed to save notification preferences")
      setTimeout(() => setNotificationsError(null), 5000)
    } finally {
      setIsSavingNotifications(false)
    }
  }

  const handleDeleteAccount = async () => {
    if (!confirm("Are you sure you want to delete your account? This action cannot be undone.")) {
      return
    }

    setIsDeleting(true)
    try {
      // Delete account from backend
      await authService.deleteAccount()
      // Clear local session
      await logout()
      router.push("/")
    } catch (error) {
      console.error("Failed to delete account:", error)
      setProfileError(error instanceof Error ? error.message : "Failed to delete account")
      setIsDeleting(false)
    }
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A"
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    })
  }

  const getTierBadgeColor = (tier: string) => {
    switch (tier) {
      case "enterprise":
        return "bg-purple-50 text-purple-700"
      case "paid":
        return "bg-blue-50 text-blue-700"
      default:
        return "bg-gray-50 text-gray-700"
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen bg-white">
      <Header />
      <Sidebar />

      <main className="md:pl-64 pt-14">
        <div className="max-w-6xl mx-auto px-4 md:px-12 py-8 md:py-12">
          <h1 className="text-3xl md:text-4xl font-normal text-black mb-2">Settings</h1>
          <p className="text-gray-600 mb-8 md:mb-12">Manage your account settings and preferences</p>

          <div className="flex flex-col md:flex-row gap-6 md:gap-12">
            {/* Settings Navigation - Horizontal scroll on mobile, vertical on desktop */}
            <nav className="w-full md:w-48 flex-shrink-0">
              <div className="flex md:flex-col gap-1 overflow-x-auto pb-2 md:pb-0 -mx-4 px-4 md:mx-0 md:px-0">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`whitespace-nowrap px-4 py-2.5 text-sm rounded-lg transition-colors min-h-[44px] ${
                      activeTab === tab.id
                        ? "bg-gray-100 text-black font-medium"
                        : "text-gray-600 hover:text-black hover:bg-gray-50"
                    } md:w-full md:text-left`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </nav>

            {/* Settings Content */}
            <div className="flex-1 min-w-0">
              {activeTab === "general" && (
                <div className="space-y-8">
                  <div>
                    <h2 className="text-xl font-normal text-black mb-6">General Settings</h2>

                    <div className="space-y-6">
                      <div>
                        <label className="block text-sm text-gray-900 mb-2">Full Name</label>
                        <input
                          type="text"
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          placeholder="Enter your full name"
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                        />
                      </div>

                      <div>
                        <label className="block text-sm text-gray-900 mb-2">Email Address</label>
                        <input
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                        />
                        <p className="mt-1 text-xs text-gray-500">
                          {user.email_confirmed_at 
                            ? `Email verified on ${formatDate(user.email_confirmed_at)}`
                            : "Email not verified"
                          }
                        </p>
                      </div>

                      {/* Account Info Display */}
                      <div className="p-4 bg-gray-50 rounded-lg space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Account Tier</span>
                          <span className={`px-2 py-1 text-xs rounded capitalize ${getTierBadgeColor(user.tier)}`}>
                            {user.tier}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Member Since</span>
                          <span className="text-sm text-gray-900">{formatDate(user.created_at)}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Last Login</span>
                          <span className="text-sm text-gray-900">{formatDate(user.last_login || user.last_sign_in_at)}</span>
                        </div>
                        {user.role && user.role !== "user" && (
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-600">Role</span>
                            <span className="px-2 py-1 text-xs bg-green-50 text-green-700 rounded capitalize">
                              {user.role}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {profileError && (
                    <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                      <AlertCircle className="w-4 h-4" />
                      {profileError}
                    </div>
                  )}

                  {profileSuccess && (
                    <div className="flex items-center gap-2 p-3 bg-green-50 text-green-700 rounded-lg text-sm">
                      <Check className="w-4 h-4" />
                      Profile updated successfully
                    </div>
                  )}

                  <div className="pt-6 border-t border-gray-200">
                    <Button 
                      onClick={handleSaveProfile}
                      disabled={isSavingProfile}
                      className="bg-black text-white hover:bg-gray-800 px-6 text-sm font-normal"
                    >
                      {isSavingProfile ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        "Save changes"
                      )}
                    </Button>
                  </div>
                </div>
              )}

              {activeTab === "account" && (
                <div className="space-y-8">
                  <div>
                    <h2 className="text-xl font-normal text-black mb-6">Account Information</h2>

                    <div className="space-y-6">
                      {/* Subscription Info */}
                      <div className="p-6 border border-gray-200 rounded-lg">
                        <h3 className="text-lg font-normal text-black mb-4">Subscription</h3>
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-600">Current Plan</span>
                            <span className={`px-3 py-1 text-sm rounded-full capitalize ${getTierBadgeColor(user.tier)}`}>
                              {user.tier} Plan
                            </span>
                          </div>
                          {user.subscription_start && (
                            <div className="flex items-center justify-between">
                              <span className="text-sm text-gray-600">Started</span>
                              <span className="text-sm text-gray-900">{formatDate(user.subscription_start)}</span>
                            </div>
                          )}
                          {user.subscription_end && (
                            <div className="flex items-center justify-between">
                              <span className="text-sm text-gray-600">Renews</span>
                              <span className="text-sm text-gray-900">{formatDate(user.subscription_end)}</span>
                            </div>
                          )}
                        </div>
                        {user.tier === "free" && (
                          <div className="mt-4 pt-4 border-t border-gray-100">
                            <Button 
                              variant="outline" 
                              className="border-gray-300 text-sm font-normal bg-transparent"
                              onClick={() => router.push("/pricing")}
                            >
                              Upgrade to Pro
                            </Button>
                          </div>
                        )}
                      </div>

                      {/* Account Details */}
                      <div className="p-6 border border-gray-200 rounded-lg">
                        <h3 className="text-lg font-normal text-black mb-4">Account Details</h3>
                        <div className="space-y-3">
                          <div className="flex items-center justify-between py-2 border-b border-gray-100">
                            <span className="text-sm text-gray-600">User ID</span>
                            <code className="text-xs text-gray-500 bg-gray-50 px-2 py-1 rounded">
                              {user.id.slice(0, 8)}...{user.id.slice(-4)}
                            </code>
                          </div>
                          <div className="flex items-center justify-between py-2 border-b border-gray-100">
                            <span className="text-sm text-gray-600">Email</span>
                            <span className="text-sm text-gray-900">{user.email}</span>
                          </div>
                          <div className="flex items-center justify-between py-2">
                            <span className="text-sm text-gray-600">Account Status</span>
                            <span className="px-2 py-1 text-xs bg-green-50 text-green-700 rounded">
                              Active
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="pt-6 border-t border-gray-200">
                    <h3 className="text-lg font-normal text-black mb-4">Danger Zone</h3>
                    <div className="space-y-4">
                      <div className="p-4 border border-red-200 rounded-lg bg-red-50">
                        <h4 className="text-sm font-medium text-red-900 mb-2">Delete Account</h4>
                        <p className="text-sm text-red-700 mb-4">
                          Once you delete your account, there is no going back. All your data including watchlists and settings will be permanently removed.
                        </p>
                        <Button
                          variant="outline"
                          onClick={handleDeleteAccount}
                          disabled={isDeleting}
                          className="border-red-300 text-red-700 hover:bg-red-100 bg-transparent"
                        >
                          {isDeleting ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Deleting...
                            </>
                          ) : (
                            "Delete account"
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "security" && (
                <div className="space-y-8">
                  <div>
                    <h2 className="text-xl font-normal text-black mb-6">Security Settings</h2>

                    {/* Check if user signed in with OAuth provider (Google, Apple, etc.) */}
                    {user?.app_metadata?.provider && user.app_metadata.provider !== 'email' ? (
                      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                        <div className="flex items-start gap-3">
                          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
                          <div>
                            <h4 className="text-sm font-medium text-blue-900 mb-1">
                              Signed in with {String(user.app_metadata.provider).charAt(0).toUpperCase() + String(user.app_metadata.provider).slice(1)}
                            </h4>
                            <p className="text-sm text-blue-700">
                              Password management is not available for accounts using social sign-in. 
                              Your account security is managed through your {String(user.app_metadata.provider).charAt(0).toUpperCase() + String(user.app_metadata.provider).slice(1)} account.
                            </p>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="space-y-6">
                          <div>
                            <label className="block text-sm text-gray-900 mb-2">Current Password</label>
                            <div className="relative">
                              <input
                                type={showCurrentPassword ? "text" : "password"}
                                value={currentPassword}
                                onChange={(e) => setCurrentPassword(e.target.value)}
                                placeholder="Enter current password"
                                className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                              />
                              <button
                                type="button"
                                onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                              >
                                {showCurrentPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                              </button>
                            </div>
                          </div>

                          <div>
                            <label className="block text-sm text-gray-900 mb-2">New Password</label>
                            <div className="relative">
                              <input
                                type={showNewPassword ? "text" : "password"}
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                placeholder="Enter new password (min. 8 characters)"
                                className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                              />
                              <button
                                type="button"
                                onClick={() => setShowNewPassword(!showNewPassword)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                              >
                                {showNewPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                              </button>
                            </div>
                          </div>

                          <div>
                            <label className="block text-sm text-gray-900 mb-2">Confirm New Password</label>
                            <div className="relative">
                              <input
                                type={showConfirmPassword ? "text" : "password"}
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="Confirm new password"
                                className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                              />
                              <button
                                type="button"
                                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                              >
                                {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                              </button>
                            </div>
                          </div>
                        </div>

                        {passwordError && (
                          <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                            <AlertCircle className="w-4 h-4" />
                            {passwordError}
                          </div>
                        )}

                        {passwordSuccess && (
                          <div className="flex items-center gap-2 p-3 bg-green-50 text-green-700 rounded-lg text-sm">
                            <Check className="w-4 h-4" />
                            Password updated successfully
                          </div>
                        )}

                        <div className="pt-6 border-t border-gray-200">
                          <Button 
                            onClick={handleUpdatePassword}
                            disabled={isSavingPassword || !newPassword || !confirmPassword}
                            className="bg-black text-white hover:bg-gray-800 px-6 text-sm font-normal"
                          >
                            {isSavingPassword ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Updating...
                              </>
                            ) : (
                              "Update password"
                            )}
                          </Button>
                        </div>
                      </>
                    )}
                  </div>

                  <div className="pt-6 border-t border-gray-200">
                    <h3 className="text-lg font-normal text-black mb-4">Two-Factor Authentication</h3>
                    <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 mb-1">Authenticator App</h4>
                        <p className="text-sm text-gray-600">Use an authenticator app to generate one-time codes</p>
                      </div>
                      <Button variant="outline" className="border-gray-300 text-sm font-normal bg-transparent" disabled>
                        Coming Soon
                      </Button>
                    </div>
                  </div>

                  <div className="pt-6 border-t border-gray-200">
                    <h3 className="text-lg font-normal text-black mb-4">Login Activity</h3>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm text-gray-900">Last sign in</p>
                          <p className="text-xs text-gray-500">{formatDate(user.last_sign_in_at)}</p>
                        </div>
                        <span className="px-2 py-1 text-xs bg-green-50 text-green-700 rounded">Current Session</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "notifications" && (
                <div className="space-y-8">
                  <div>
                    <h2 className="text-xl font-normal text-black mb-6">Notification Preferences</h2>

                    <div className="space-y-6">
                      <div className="flex items-center justify-between py-4 border-b border-gray-100">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-1">Email Notifications</h4>
                          <p className="text-sm text-gray-600">Receive email updates about your account</p>
                        </div>
                        <input 
                          type="checkbox" 
                          checked={notifications.email_notifications}
                          onChange={(e) => setNotifications({...notifications, email_notifications: e.target.checked})}
                          className="w-4 h-4 rounded border-gray-300 accent-black" 
                        />
                      </div>

                      <div className="flex items-center justify-between py-4 border-b border-gray-100">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-1">Product Updates</h4>
                          <p className="text-sm text-gray-600">Get notified about new features and updates</p>
                        </div>
                        <input 
                          type="checkbox" 
                          checked={notifications.product_updates}
                          onChange={(e) => setNotifications({...notifications, product_updates: e.target.checked})}
                          className="w-4 h-4 rounded border-gray-300 accent-black" 
                        />
                      </div>

                      <div className="flex items-center justify-between py-4 border-b border-gray-100">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-1">Price Alerts</h4>
                          <p className="text-sm text-gray-600">Alerts when your watchlist stocks hit target prices</p>
                        </div>
                        <input 
                          type="checkbox" 
                          checked={notifications.usage_alerts}
                          onChange={(e) => setNotifications({...notifications, usage_alerts: e.target.checked})}
                          className="w-4 h-4 rounded border-gray-300 accent-black" 
                        />
                      </div>

                      <div className="flex items-center justify-between py-4 border-b border-gray-100">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-1">Stock News</h4>
                          <p className="text-sm text-gray-600">Daily morning summary with stock news and prices</p>
                        </div>
                        <input 
                          type="checkbox" 
                          checked={notifications.stock_news}
                          onChange={(e) => setNotifications({...notifications, stock_news: e.target.checked})}
                          className="w-4 h-4 rounded border-gray-300 accent-black" 
                        />
                      </div>

                      <div className="flex items-center justify-between py-4 border-b border-gray-100">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-1">Marketing Emails</h4>
                          <p className="text-sm text-gray-600">Receive tips, tutorials, and case studies</p>
                        </div>
                        <input 
                          type="checkbox" 
                          checked={notifications.marketing_emails}
                          onChange={(e) => setNotifications({...notifications, marketing_emails: e.target.checked})}
                          className="w-4 h-4 rounded border-gray-300 accent-black" 
                        />
                      </div>
                    </div>
                  </div>

                  {notificationsSuccess && (
                    <div className="flex items-center gap-2 p-3 bg-green-50 text-green-700 rounded-lg text-sm">
                      <Check className="w-4 h-4" />
                      Preferences saved successfully
                    </div>
                  )}

                  {notificationsError && (
                    <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                      <AlertCircle className="w-4 h-4" />
                      {notificationsError}
                    </div>
                  )}

                  {isLoadingNotifications && (
                    <div className="flex items-center gap-2 p-3 bg-blue-50 text-blue-700 rounded-lg text-sm">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Loading preferences...
                    </div>
                  )}

                  <div className="pt-6 border-t border-gray-200">
                    <Button 
                      onClick={handleSaveNotifications}
                      disabled={isSavingNotifications || isLoadingNotifications}
                      className="bg-black text-white hover:bg-gray-800 px-6 text-sm font-normal"
                    >
                      {isSavingNotifications ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        "Save preferences"
                      )}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

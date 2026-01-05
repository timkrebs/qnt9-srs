"use client"

import Header from "@/components/header"
import Sidebar from "@/components/sidebar"
import { Button } from "@/components/ui/button"
import { useState } from "react"

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("general")

  const tabs = [
    { id: "general", label: "General" },
    { id: "account", label: "Account" },
    { id: "security", label: "Security" },
    { id: "api", label: "API Keys" },
    { id: "billing", label: "Billing" },
    { id: "notifications", label: "Notifications" },
  ]

  return (
    <div className="min-h-screen bg-white">
      <Header />
      <Sidebar />

      <main className="pl-64 pt-14">
        <div className="max-w-6xl mx-auto px-12 py-12">
          <h1 className="text-4xl font-normal text-black mb-2">Settings</h1>
          <p className="text-gray-600 mb-12">Manage your account settings and preferences</p>

          <div className="flex gap-12">
            {/* Settings Navigation */}
            <nav className="w-48 flex-shrink-0">
              <div className="space-y-1">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full text-left px-4 py-2 text-sm rounded-lg transition-colors ${
                      activeTab === tab.id
                        ? "bg-gray-100 text-black font-medium"
                        : "text-gray-600 hover:text-black hover:bg-gray-50"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </nav>

            {/* Settings Content */}
            <div className="flex-1">
              {activeTab === "general" && (
                <div className="space-y-8">
                  <div>
                    <h2 className="text-xl font-normal text-black mb-6">General Settings</h2>

                    <div className="space-y-6">
                      <div>
                        <label className="block text-sm text-gray-900 mb-2">Profile Name</label>
                        <input
                          type="text"
                          defaultValue="John Doe"
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                        />
                      </div>

                      <div>
                        <label className="block text-sm text-gray-900 mb-2">Bio</label>
                        <textarea
                          rows={4}
                          defaultValue="Building the future of AI applications with OpenAI's platform."
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                        />
                      </div>

                      <div>
                        <label className="block text-sm text-gray-900 mb-2">Location</label>
                        <input
                          type="text"
                          defaultValue="San Francisco, CA"
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                        />
                      </div>

                      <div>
                        <label className="block text-sm text-gray-900 mb-2">Language</label>
                        <select className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent">
                          <option>English (US)</option>
                          <option>English (UK)</option>
                          <option>Spanish</option>
                          <option>French</option>
                          <option>German</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="pt-6 border-t border-gray-200">
                    <Button className="bg-black text-white hover:bg-gray-800 px-6 text-sm font-normal">
                      Save changes
                    </Button>
                  </div>
                </div>
              )}

              {activeTab === "account" && (
                <div className="space-y-8">
                  <div>
                    <h2 className="text-xl font-normal text-black mb-6">Account Settings</h2>

                    <div className="space-y-6">
                      <div>
                        <label className="block text-sm text-gray-900 mb-2">Email Address</label>
                        <input
                          type="email"
                          defaultValue="john.doe@example.com"
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                        />
                        <p className="mt-1 text-xs text-gray-500">
                          Your email address is used for login and notifications
                        </p>
                      </div>

                      <div>
                        <label className="block text-sm text-gray-900 mb-2">Username</label>
                        <input
                          type="text"
                          defaultValue="johndoe"
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                        />
                      </div>

                      <div>
                        <label className="block text-sm text-gray-900 mb-2">Organization</label>
                        <input
                          type="text"
                          placeholder="Your organization name (optional)"
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="pt-6 border-t border-gray-200">
                    <h3 className="text-lg font-normal text-black mb-4">Danger Zone</h3>
                    <div className="space-y-4">
                      <div className="p-4 border border-red-200 rounded-lg bg-red-50">
                        <h4 className="text-sm font-medium text-red-900 mb-2">Delete Account</h4>
                        <p className="text-sm text-red-700 mb-4">
                          Once you delete your account, there is no going back. Please be certain.
                        </p>
                        <Button
                          variant="outline"
                          className="border-red-300 text-red-700 hover:bg-red-100 bg-transparent"
                        >
                          Delete account
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

                    <div className="space-y-6">
                      <div>
                        <label className="block text-sm text-gray-900 mb-2">Current Password</label>
                        <input
                          type="password"
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                        />
                      </div>

                      <div>
                        <label className="block text-sm text-gray-900 mb-2">New Password</label>
                        <input
                          type="password"
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                        />
                      </div>

                      <div>
                        <label className="block text-sm text-gray-900 mb-2">Confirm New Password</label>
                        <input
                          type="password"
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="pt-6 border-t border-gray-200">
                    <h3 className="text-lg font-normal text-black mb-4">Two-Factor Authentication</h3>
                    <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 mb-1">Authenticator App</h4>
                        <p className="text-sm text-gray-600">Use an authenticator app to generate one-time codes</p>
                      </div>
                      <Button variant="outline" className="border-gray-300 text-sm font-normal bg-transparent">
                        Enable
                      </Button>
                    </div>
                  </div>

                  <div className="pt-6 border-t border-gray-200">
                    <Button className="bg-black text-white hover:bg-gray-800 px-6 text-sm font-normal">
                      Update password
                    </Button>
                  </div>
                </div>
              )}

              {activeTab === "api" && (
                <div className="space-y-8">
                  <div>
                    <h2 className="text-xl font-normal text-black mb-2">API Keys</h2>
                    <p className="text-sm text-gray-600 mb-6">Manage your API keys for accessing OpenAI services</p>

                    <div className="space-y-4">
                      <div className="p-4 border border-gray-200 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-sm font-medium text-gray-900">Production Key</h4>
                          <span className="px-2 py-1 text-xs bg-green-50 text-green-700 rounded">Active</span>
                        </div>
                        <p className="text-sm text-gray-600 font-mono mb-2">sk-...7a3f</p>
                        <p className="text-xs text-gray-500">Created on Jan 15, 2024</p>
                      </div>

                      <div className="p-4 border border-gray-200 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-sm font-medium text-gray-900">Development Key</h4>
                          <span className="px-2 py-1 text-xs bg-green-50 text-green-700 rounded">Active</span>
                        </div>
                        <p className="text-sm text-gray-600 font-mono mb-2">sk-...2b9c</p>
                        <p className="text-xs text-gray-500">Created on Dec 8, 2023</p>
                      </div>
                    </div>
                  </div>

                  <div className="pt-6 border-t border-gray-200">
                    <Button className="bg-black text-white hover:bg-gray-800 px-6 text-sm font-normal">
                      Create new key
                    </Button>
                  </div>
                </div>
              )}

              {activeTab === "billing" && (
                <div className="space-y-8">
                  <div>
                    <h2 className="text-xl font-normal text-black mb-6">Billing & Usage</h2>

                    <div className="p-6 border border-gray-200 rounded-lg mb-6">
                      <h3 className="text-lg font-normal text-black mb-4">Current Plan</h3>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm text-gray-900 font-medium mb-1">Pro Plan</p>
                          <p className="text-sm text-gray-600">$20/month</p>
                        </div>
                        <Button variant="outline" className="border-gray-300 text-sm font-normal bg-transparent">
                          Change plan
                        </Button>
                      </div>
                    </div>

                    <div>
                      <h3 className="text-lg font-normal text-black mb-4">Usage this month</h3>
                      <div className="space-y-4">
                        <div className="flex items-center justify-between py-3 border-b border-gray-100">
                          <span className="text-sm text-gray-900">API Calls</span>
                          <span className="text-sm font-medium text-gray-900">47,328</span>
                        </div>
                        <div className="flex items-center justify-between py-3 border-b border-gray-100">
                          <span className="text-sm text-gray-900">Tokens Used</span>
                          <span className="text-sm font-medium text-gray-900">1,234,567</span>
                        </div>
                        <div className="flex items-center justify-between py-3 border-b border-gray-100">
                          <span className="text-sm text-gray-900">Estimated Cost</span>
                          <span className="text-sm font-medium text-gray-900">$47.32</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="pt-6 border-t border-gray-200">
                    <h3 className="text-lg font-normal text-black mb-4">Payment Method</h3>
                    <div className="p-4 border border-gray-200 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-12 h-8 bg-gray-900 rounded flex items-center justify-center text-white text-xs font-bold">
                            VISA
                          </div>
                          <div>
                            <p className="text-sm text-gray-900">•••• •••• •••• 4242</p>
                            <p className="text-xs text-gray-500">Expires 12/25</p>
                          </div>
                        </div>
                        <Button variant="outline" className="border-gray-300 text-sm font-normal bg-transparent">
                          Update
                        </Button>
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
                        <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-gray-300" />
                      </div>

                      <div className="flex items-center justify-between py-4 border-b border-gray-100">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-1">Product Updates</h4>
                          <p className="text-sm text-gray-600">Get notified about new features and updates</p>
                        </div>
                        <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-gray-300" />
                      </div>

                      <div className="flex items-center justify-between py-4 border-b border-gray-100">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-1">Usage Alerts</h4>
                          <p className="text-sm text-gray-600">Alerts when you're approaching usage limits</p>
                        </div>
                        <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-gray-300" />
                      </div>

                      <div className="flex items-center justify-between py-4 border-b border-gray-100">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-1">Security Alerts</h4>
                          <p className="text-sm text-gray-600">Important security updates and notifications</p>
                        </div>
                        <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-gray-300" />
                      </div>

                      <div className="flex items-center justify-between py-4 border-b border-gray-100">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-1">Marketing Emails</h4>
                          <p className="text-sm text-gray-600">Receive tips, tutorials, and case studies</p>
                        </div>
                        <input type="checkbox" className="w-4 h-4 rounded border-gray-300" />
                      </div>
                    </div>
                  </div>

                  <div className="pt-6 border-t border-gray-200">
                    <Button className="bg-black text-white hover:bg-gray-800 px-6 text-sm font-normal">
                      Save preferences
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

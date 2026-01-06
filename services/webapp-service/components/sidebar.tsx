"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Star } from "lucide-react"
import { useAuth } from "@/lib/auth/auth-context"

export default function Sidebar() {
  const pathname = usePathname()
  const { isAuthenticated } = useAuth()

  const menuItems = [
    { label: "Research", href: "/research" },
    { label: "Safety", href: "/safety" },
    { label: "For Business", href: "/for-business" },
    { label: "For Developers", href: "/for-developers" },
    { label: "ChatGPT", href: "/chatgpt" },
    { label: "Sora", href: "/sora" },
    { label: "Stories", href: "/stories" },
    { label: "Company", href: "/company" },
    { label: "News", href: "/news" },
  ]

  // Hide sidebar on specific pages and on mobile (mobile uses header drawer instead)
  if (
    pathname === "/search" ||
    pathname === "/login" ||
    pathname === "/signup" ||
    pathname === "/profile" ||
    pathname === "/settings" ||
    pathname === "/watchlist"
  ) {
    return null
  }

  return (
    <aside className="hidden md:block fixed left-0 top-14 w-64 h-[calc(100vh-3.5rem)] bg-white border-r border-gray-200 pt-8 px-6">
      {/* Watchlist Link for Authenticated Users */}
      {isAuthenticated && (
        <div className="mb-6 pb-6 border-b border-gray-200">
          <Link
            href="/watchlist"
            className={`flex items-center gap-2 px-0 py-2 text-sm transition-colors ${
              pathname === "/watchlist"
                ? "text-black font-medium"
                : "text-gray-600 hover:text-black"
            }`}
          >
            <Star className="w-4 h-4" />
            <span>My Watchlist</span>
          </Link>
        </div>
      )}

      <nav className="space-y-1">
        {menuItems.map((item) => (
          <Link
            key={item.label}
            href={item.href}
            className={`block w-full text-left px-0 py-2 text-sm transition-colors ${
              pathname === item.href ? "text-black font-medium" : "text-gray-600 hover:text-black"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  )
}

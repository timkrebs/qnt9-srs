'use client'

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { usePathname, useRouter } from 'next/navigation'
import { Search, Settings, User, LogOut, FileEdit, Menu, Star, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetClose,
} from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/lib/auth/auth-context'
import { useToast } from '@/hooks/use-toast'
import { cn } from '@/lib/utils'

const NAV_LINKS = [
  { label: "Home", href: "/" },
  { label: "Pricing", href: "/pricing" },
  { label: "Docs", href: "/docs" },
  { label: "About", href: "/about" },
]

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

export default function Header() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, isLoading, isAuthenticated, logout, canManageBlog } = useAuth()
  const { toast } = useToast()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const isAuthPage = pathname === '/login' || pathname === '/signup'

  const handleCloseMobileMenu = () => {
    setMobileMenuOpen(false)
  }

  const handleLogout = async () => {
    handleCloseMobileMenu()
    try {
      await logout()
      toast({
        title: 'Signed out',
        description: 'You have been signed out successfully.',
      })
      router.push('/')
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to sign out. Please try again.',
        variant: 'destructive',
      })
    }
  }

  const renderAuthSection = () => {
    if (isLoading) {
      return <Skeleton className="h-8 w-20 rounded-full" />
    }

    if (isAuthenticated && user) {
      return (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="w-8 h-8 rounded-full p-0"
              aria-label="User menu"
            >
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-black text-white text-xs font-medium">
                  {getInitials(user.full_name, user.email)}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                {user.full_name && (
                  <p className="text-sm font-medium leading-none">
                    {user.full_name}
                  </p>
                )}
                <p className="text-xs leading-none text-muted-foreground">
                  {user.email}
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link
                href="/profile"
                className="cursor-pointer flex items-center"
              >
                <User className="mr-2 h-4 w-4" />
                Profile
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link
                href="/settings"
                className="cursor-pointer flex items-center"
              >
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </Link>
            </DropdownMenuItem>
            {canManageBlog && (
              <DropdownMenuItem asChild>
                <Link
                  href="/admin/blog"
                  className="cursor-pointer flex items-center"
                >
                  <FileEdit className="mr-2 h-4 w-4" />
                  Blog Admin
                </Link>
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={handleLogout}
              className="cursor-pointer text-destructive focus:text-destructive"
            >
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
    }

    return (
      <div className="flex items-center gap-2">
        <Link href="/login">
          <Button variant="ghost" className="text-sm font-normal">
            Log in
          </Button>
        </Link>
        <Link href="/signup">
          <Button className="bg-black text-white hover:bg-gray-800 text-sm font-normal">
            Sign up
          </Button>
        </Link>
      </div>
    )
  }

  return (
    <>
      <header className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-4 md:px-8 h-14">
          <div className="flex items-center gap-4 md:gap-8">
            {/* Mobile Menu Button */}
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden w-10 h-10"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="w-5 h-5" />
            </Button>

            <Link href="/" className="flex items-center gap-2">
              <Image 
                src="/logo.png" 
                alt="finio" 
                width={36} 
                height={36} 
                className="rounded-sm"
              />
              <span className="text-xl font-semibold text-black">finio</span>
            </Link>
            
            {/* Desktop Navigation Links */}
            <nav className="hidden md:flex items-center gap-6">
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "text-sm font-medium transition-colors hover:text-gray-900",
                    pathname === link.href ? "text-gray-900" : "text-gray-500"
                  )}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-1 md:gap-2">
            <Link href="/search">
              <Button
                variant="ghost"
                size="icon"
                className="w-10 h-10"
                aria-label="Search"
              >
                <Search className="w-5 h-5" />
              </Button>
            </Link>

            {/* Desktop Auth Section */}
            <div className="hidden md:flex items-center">
              {!isAuthPage && renderAuthSection()}

              {isAuthPage && !isAuthenticated && (
                <Link href="/login">
                  <Button variant="ghost" className="text-sm font-normal">
                    Log in
                  </Button>
                </Link>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Mobile Navigation Drawer */}
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" className="w-80 p-0">
          <SheetHeader className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <SheetTitle className="flex items-center gap-2">
                <Image 
                  src="/logo.png" 
                  alt="finio" 
                  width={32} 
                  height={32} 
                  className="rounded-sm"
                />
                <span className="text-lg font-semibold">finio</span>
              </SheetTitle>
            </div>
          </SheetHeader>

          <div className="flex flex-col h-[calc(100%-65px)]">
            {/* User Info for Mobile */}
            {isAuthenticated && user && (
              <div className="p-4 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center gap-3">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback className="bg-black text-white text-sm font-medium">
                      {getInitials(user.full_name, user.email)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    {user.full_name && (
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {user.full_name}
                      </p>
                    )}
                    <p className="text-xs text-gray-500 truncate">
                      {user.email}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Watchlist Link for Authenticated Users */}
            {isAuthenticated && (
              <div className="p-4 border-b border-gray-200">
                <Link
                  href="/watchlist"
                  onClick={handleCloseMobileMenu}
                  className={cn(
                    "flex items-center gap-3 py-2 text-sm transition-colors",
                    pathname === "/watchlist"
                      ? "text-black font-medium"
                      : "text-gray-600"
                  )}
                >
                  <Star className="w-5 h-5" />
                  <span>My Watchlist</span>
                </Link>
              </div>
            )}

            {/* Main Navigation */}
            <nav className="flex-1 overflow-y-auto p-4">
              <div className="space-y-1">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                  Navigation
                </p>
                {NAV_LINKS.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={handleCloseMobileMenu}
                    className={cn(
                      "block py-2.5 text-sm transition-colors",
                      pathname === link.href
                        ? "text-black font-medium"
                        : "text-gray-600"
                    )}
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </nav>

            {/* Mobile Footer Actions */}
            <div className="p-4 border-t border-gray-200 bg-gray-50">
              {isAuthenticated ? (
                <div className="space-y-2">
                  <Link
                    href="/profile"
                    onClick={handleCloseMobileMenu}
                    className="flex items-center gap-3 py-2.5 text-sm text-gray-600"
                  >
                    <User className="w-5 h-5" />
                    Profile
                  </Link>
                  <Link
                    href="/settings"
                    onClick={handleCloseMobileMenu}
                    className="flex items-center gap-3 py-2.5 text-sm text-gray-600"
                  >
                    <Settings className="w-5 h-5" />
                    Settings
                  </Link>
                  {canManageBlog && (
                    <Link
                      href="/admin/blog"
                      onClick={handleCloseMobileMenu}
                      className="flex items-center gap-3 py-2.5 text-sm text-gray-600"
                    >
                      <FileEdit className="w-5 h-5" />
                      Blog Admin
                    </Link>
                  )}
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-3 py-2.5 text-sm text-red-600 w-full"
                  >
                    <LogOut className="w-5 h-5" />
                    Sign out
                  </button>
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  <Link href="/login" onClick={handleCloseMobileMenu}>
                    <Button variant="outline" className="w-full h-11">
                      Log in
                    </Button>
                  </Link>
                  <Link href="/signup" onClick={handleCloseMobileMenu}>
                    <Button className="w-full h-11 bg-black text-white hover:bg-gray-800">
                      Sign up
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}

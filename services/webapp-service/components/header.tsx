'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { Search, Settings, User, LogOut, FileEdit } from 'lucide-react'
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

  const isAuthPage = pathname === '/login' || pathname === '/signup'

  const handleLogout = async () => {
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
    <header className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200">
      <div className="max-w-6xl mx-auto flex items-center justify-between px-6 md:px-8 h-14">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-xl font-semibold text-black">QNT9</span>
          </Link>
          
          {/* Navigation Links */}
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

        <div className="flex items-center gap-2">
          <Link href="/search">
            <Button
              variant="ghost"
              size="icon"
              className="w-8 h-8"
              aria-label="Search"
            >
              <Search className="w-4 h-4" />
            </Button>
          </Link>

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
    </header>
  )
}

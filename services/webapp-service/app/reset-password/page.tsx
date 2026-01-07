'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import Header from '@/components/header'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { useToast } from '@/hooks/use-toast'
import { authService } from '@/lib/api/auth'
import { ApiError } from '@/lib/api/client'
import { getPasswordStrength } from '@/lib/validations/auth'
import { ArrowLeft, CheckCircle, XCircle, KeyRound, AlertTriangle } from 'lucide-react'

const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .max(128, 'Password must be at most 128 characters')
  .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
  .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
  .regex(/[0-9]/, 'Password must contain at least one digit')
  .regex(
    /[!@#$%^&*(),.?":{}|<>_\-+=[\]\\;'`~]/,
    'Password must contain at least one special character',
  )

const resetPasswordSchema = z.object({
  password: passwordSchema,
  confirmPassword: z.string().min(1, 'Please confirm your password'),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
})

type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>

// Token extraction types
interface TokenData {
  accessToken: string | null
  refreshToken: string | null
  type: string | null
  error: string | null
}

function extractTokensFromUrl(): TokenData {
  if (typeof window === 'undefined') {
    return { accessToken: null, refreshToken: null, type: null, error: null }
  }

  // Supabase sends tokens in URL hash fragment for PKCE flow
  // Format: #access_token=xxx&refresh_token=xxx&type=recovery&...
  const hash = window.location.hash.substring(1)
  const params = new URLSearchParams(hash)

  // Also check query params as fallback
  const searchParams = new URLSearchParams(window.location.search)

  const accessToken = params.get('access_token') || searchParams.get('access_token')
  const refreshToken = params.get('refresh_token') || searchParams.get('refresh_token')
  const type = params.get('type') || searchParams.get('type')
  const error = params.get('error') || searchParams.get('error')
  const errorDescription = params.get('error_description') || searchParams.get('error_description')

  return {
    accessToken,
    refreshToken,
    type,
    error: error ? (errorDescription || error) : null,
  }
}

function ResetPasswordContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { toast } = useToast()
  
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const [tokenError, setTokenError] = useState<string | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const form = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      password: '',
      confirmPassword: '',
    },
  })

  const password = form.watch('password')
  const passwordStrength = getPasswordStrength(password || '')

  // Extract tokens on mount
  useEffect(() => {
    const tokens = extractTokensFromUrl()

    if (tokens.error) {
      setTokenError(tokens.error)
      setIsLoading(false)
      return
    }

    if (!tokens.accessToken) {
      setTokenError('Invalid or missing reset link. Please request a new password reset.')
      setIsLoading(false)
      return
    }

    // Verify this is a recovery token
    if (tokens.type && tokens.type !== 'recovery') {
      setTokenError('Invalid reset link type. Please request a new password reset.')
      setIsLoading(false)
      return
    }

    setAccessToken(tokens.accessToken)
    setIsLoading(false)

    // Clean up URL hash to prevent token exposure in browser history
    if (window.location.hash) {
      window.history.replaceState(null, '', window.location.pathname)
    }
  }, [searchParams])

  const handleSubmit = async (data: ResetPasswordFormData) => {
    if (!accessToken) {
      setTokenError('Reset token is missing. Please request a new password reset.')
      return
    }

    setIsSubmitting(true)
    try {
      await authService.updatePasswordWithToken(accessToken, data.password)
      setIsSuccess(true)
      toast({
        title: 'Password updated',
        description: 'Your password has been successfully reset.',
      })
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Failed to reset password. Please try again.'
      
      // Check for expired token
      if (message.toLowerCase().includes('expired') || message.toLowerCase().includes('invalid')) {
        setTokenError('Your reset link has expired. Please request a new one.')
      } else {
        toast({
          title: 'Password reset failed',
          description: message,
          variant: 'destructive',
        })
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-white">
        <Header />
        <main className="pt-14 flex items-center justify-center min-h-screen">
          <div className="flex flex-col items-center gap-4">
            <Spinner className="size-8" />
            <p className="text-sm text-gray-600">Verifying reset link...</p>
          </div>
        </main>
      </div>
    )
  }

  // Error state - invalid or expired token
  if (tokenError) {
    return (
      <div className="min-h-screen bg-white">
        <Header />
        <main className="pt-14 flex items-center justify-center min-h-screen">
          <div className="w-full max-w-md px-4 py-12">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-6">
                <XCircle className="w-8 h-8 text-red-600" />
              </div>
              
              <h1 className="text-2xl font-normal text-black mb-2">
                Reset link invalid
              </h1>
              <p className="text-sm text-gray-600 mb-8">
                {tokenError}
              </p>

              <div className="space-y-4">
                <Link href="/forgot-password">
                  <Button className="w-full bg-black text-white hover:bg-gray-800 py-3 rounded-lg text-sm font-normal">
                    Request new reset link
                  </Button>
                </Link>
                
                <Link
                  href="/login"
                  className="inline-flex items-center justify-center gap-2 text-sm text-gray-600 hover:text-black w-full"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Back to login
                </Link>
              </div>
            </div>
          </div>
        </main>
      </div>
    )
  }

  // Success state
  if (isSuccess) {
    return (
      <div className="min-h-screen bg-white">
        <Header />
        <main className="pt-14 flex items-center justify-center min-h-screen">
          <div className="w-full max-w-md px-4 py-12">
            <div className="text-center">
              <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-6">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              
              <h1 className="text-2xl font-normal text-black mb-2">
                Password reset successful
              </h1>
              <p className="text-sm text-gray-600 mb-8">
                Your password has been updated. You can now log in with your new password.
              </p>

              <Link href="/login">
                <Button className="w-full bg-black text-white hover:bg-gray-800 py-3 rounded-lg text-sm font-normal">
                  Go to login
                </Button>
              </Link>
            </div>
          </div>
        </main>
      </div>
    )
  }

  // Form state - enter new password
  return (
    <div className="min-h-screen bg-white">
      <Header />

      <main className="pt-14 flex items-center justify-center min-h-screen">
        <div className="w-full max-w-md px-4 py-12">
          <div className="text-center mb-8">
            <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-6">
              <KeyRound className="w-8 h-8 text-gray-600" />
            </div>
            <h1 className="text-2xl font-normal text-black mb-2">
              Set new password
            </h1>
            <p className="text-sm text-gray-600">
              Enter your new password below.
            </p>
          </div>

          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(handleSubmit)}
              className="space-y-4"
            >
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm text-gray-900">
                      New password
                    </FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        placeholder="Enter new password"
                        autoComplete="new-password"
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                    
                    {/* Password strength indicator */}
                    {password && (
                      <div className="mt-2 space-y-2">
                        <div className="flex gap-1">
                          {[1, 2, 3, 4, 5, 6].map((level) => (
                            <div
                              key={level}
                              className={`h-1 flex-1 rounded-full transition-colors ${
                                level <= passwordStrength.score
                                  ? passwordStrength.color
                                  : 'bg-gray-200'
                              }`}
                            />
                          ))}
                        </div>
                        <p className="text-xs text-gray-600">
                          Password strength: {passwordStrength.label}
                        </p>
                      </div>
                    )}
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="confirmPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm text-gray-900">
                      Confirm new password
                    </FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        placeholder="Confirm new password"
                        autoComplete="new-password"
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Password requirements hint */}
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                  <div className="text-xs text-gray-600 space-y-1">
                    <p className="font-medium">Password requirements:</p>
                    <ul className="list-disc list-inside space-y-0.5">
                      <li>At least 8 characters</li>
                      <li>One uppercase letter</li>
                      <li>One lowercase letter</li>
                      <li>One number</li>
                      <li>One special character</li>
                    </ul>
                  </div>
                </div>
              </div>

              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-black text-white hover:bg-gray-800 py-3 rounded-lg text-sm font-normal"
              >
                {isSubmitting ? (
                  <span className="flex items-center justify-center gap-2">
                    <Spinner className="size-4" />
                    Updating password...
                  </span>
                ) : (
                  'Reset password'
                )}
              </Button>
            </form>
          </Form>

          <div className="mt-6 text-center">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-black"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to login
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}

// Wrap with Suspense for useSearchParams
export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-white">
          <Header />
          <main className="pt-14 flex items-center justify-center min-h-screen">
            <div className="flex flex-col items-center gap-4">
              <Spinner className="size-8" />
              <p className="text-sm text-gray-600">Loading...</p>
            </div>
          </main>
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  )
}

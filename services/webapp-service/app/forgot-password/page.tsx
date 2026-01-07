'use client'

import { useState } from 'react'
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
import { ArrowLeft, Mail, CheckCircle } from 'lucide-react'

const forgotPasswordSchema = z.object({
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address'),
})

type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>

export default function ForgotPasswordPage() {
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isEmailSent, setIsEmailSent] = useState(false)
  const [submittedEmail, setSubmittedEmail] = useState('')

  const form = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: {
      email: '',
    },
  })

  const handleSubmit = async (data: ForgotPasswordFormData) => {
    setIsSubmitting(true)
    try {
      await authService.requestPasswordReset(data.email)
      setSubmittedEmail(data.email)
      setIsEmailSent(true)
      toast({
        title: 'Reset link sent',
        description: 'Check your email for a password reset link.',
      })
    } catch (error) {
      // Always show success message for security (prevents email enumeration)
      // The backend also returns success regardless of whether email exists
      setSubmittedEmail(data.email)
      setIsEmailSent(true)
      
      // Log the actual error for debugging but dont show to user
      if (error instanceof ApiError) {
        console.error('Password reset request error:', error.message)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleResendEmail = async () => {
    if (!submittedEmail) return
    
    setIsSubmitting(true)
    try {
      await authService.requestPasswordReset(submittedEmail)
      toast({
        title: 'Reset link sent again',
        description: 'Check your email for a new password reset link.',
      })
    } catch {
      // Silently handle - same security approach as initial send
      toast({
        title: 'Reset link sent again',
        description: 'Check your email for a new password reset link.',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isEmailSent) {
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
                Check your email
              </h1>
              <p className="text-sm text-gray-600 mb-6">
                We sent a password reset link to
              </p>
              <p className="text-sm font-medium text-black mb-8">
                {submittedEmail}
              </p>

              <div className="space-y-4">
                <p className="text-sm text-gray-500">
                  Did not receive the email? Check your spam folder or
                </p>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleResendEmail}
                  disabled={isSubmitting}
                  className="w-full py-3 text-sm font-normal border-gray-300"
                >
                  {isSubmitting ? (
                    <span className="flex items-center justify-center gap-2">
                      <Spinner className="size-4" />
                      Sending...
                    </span>
                  ) : (
                    'Resend email'
                  )}
                </Button>
              </div>

              <div className="mt-8">
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-black"
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

  return (
    <div className="min-h-screen bg-white">
      <Header />

      <main className="pt-14 flex items-center justify-center min-h-screen">
        <div className="w-full max-w-md px-4 py-12">
          <div className="text-center mb-8">
            <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-6">
              <Mail className="w-8 h-8 text-gray-600" />
            </div>
            <h1 className="text-2xl font-normal text-black mb-2">
              Forgot your password?
            </h1>
            <p className="text-sm text-gray-600">
              Enter your email address and we will send you a link to reset your password.
            </p>
          </div>

          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(handleSubmit)}
              className="space-y-4"
            >
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm text-gray-900">
                      Email address
                    </FormLabel>
                    <FormControl>
                      <Input
                        type="email"
                        placeholder="you@example.com"
                        autoComplete="email"
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-black text-white hover:bg-gray-800 py-3 rounded-lg text-sm font-normal"
              >
                {isSubmitting ? (
                  <span className="flex items-center justify-center gap-2">
                    <Spinner className="size-4" />
                    Sending reset link...
                  </span>
                ) : (
                  'Send reset link'
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

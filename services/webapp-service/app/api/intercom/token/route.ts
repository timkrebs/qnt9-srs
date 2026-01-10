import { NextRequest, NextResponse } from 'next/server'
import * as jose from 'jose'

/**
 * API Route: POST /api/intercom/token
 * 
 * Generates a signed JWT for Intercom identity verification.
 * This prevents users from impersonating others in the Intercom chat.
 * 
 * The JWT is signed with the Intercom API Secret (server-side only).
 * 
 * @see https://developers.intercom.com/docs/build-an-integration/getting-started/identity-verification/
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { user_id, email } = body

    // Validate required fields
    if (!user_id) {
      return NextResponse.json(
        { error: 'user_id is required' },
        { status: 400 }
      )
    }

    // Get the Intercom API Secret (server-side only, NOT NEXT_PUBLIC_)
    const intercomSecret = process.env.INTERCOM_API_SECRET
    
    if (!intercomSecret) {
      console.error('[Intercom] INTERCOM_API_SECRET is not configured')
      return NextResponse.json(
        { error: 'Intercom identity verification not configured' },
        { status: 500 }
      )
    }

    // Create the JWT payload
    // Only include user_id and email as per Intercom's requirements
    const payload: Record<string, string> = {
      user_id: user_id,
    }

    // Add email if provided (optional but recommended)
    if (email) {
      payload.email = email
    }

    // Sign the JWT with the Intercom API Secret
    // Using jose library for Edge Runtime compatibility
    const secret = new TextEncoder().encode(intercomSecret)
    
    const token = await new jose.SignJWT(payload)
      .setProtectedHeader({ alg: 'HS256', typ: 'JWT' })
      .setIssuedAt()
      .setExpirationTime('1h') // Token expires in 1 hour
      .sign(secret)

    console.log('[Intercom] Generated JWT for user:', user_id)

    return NextResponse.json({ token })
  } catch (error) {
    console.error('[Intercom] Error generating JWT:', error)
    return NextResponse.json(
      { error: 'Failed to generate token' },
      { status: 500 }
    )
  }
}

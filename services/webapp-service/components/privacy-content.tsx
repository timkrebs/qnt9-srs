"use client"

export default function PrivacyContent() {
  const lastUpdated = "January 1, 2026"

  return (
    <main className="flex-1 pt-14">
      {/* Header */}
      <section className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-6 md:px-8 py-16">
          <h1 className="text-4xl font-semibold text-gray-900 mb-4">
            Privacy Policy
          </h1>
          <p className="text-gray-500">
            Last updated: {lastUpdated}
          </p>
        </div>
      </section>

      {/* Content */}
      <section className="max-w-4xl mx-auto px-6 md:px-8 py-12">
        <div className="prose prose-gray max-w-none">
          <p className="text-gray-600 leading-relaxed mb-8">
            At QNT9, we take your privacy seriously. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our stock research platform.
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Information We Collect
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            We collect information that you provide directly to us, including:
          </p>
          <ul className="list-disc pl-6 mb-8 space-y-2 text-gray-600">
            <li>Account information (name, email address, password)</li>
            <li>Profile information (preferences, settings)</li>
            <li>Watchlist and portfolio data</li>
            <li>Usage data and interaction with our platform</li>
            <li>Payment information (processed securely by third-party providers)</li>
          </ul>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            How We Use Your Information
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            We use the information we collect to:
          </p>
          <ul className="list-disc pl-6 mb-8 space-y-2 text-gray-600">
            <li>Provide, maintain, and improve our services</li>
            <li>Personalize your experience and deliver relevant content</li>
            <li>Process transactions and send related information</li>
            <li>Send you technical notices, updates, and support messages</li>
            <li>Respond to your comments and questions</li>
            <li>Monitor and analyze trends, usage, and activities</li>
          </ul>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Information Sharing
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            We do not sell, trade, or otherwise transfer your personal information to third parties. We may share information with trusted service providers who assist us in operating our platform, conducting our business, or servicing you, as long as they agree to keep this information confidential.
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Data Security
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            We implement appropriate technical and organizational security measures to protect your personal information against unauthorized access, alteration, disclosure, or destruction. This includes encryption of data in transit and at rest, regular security assessments, and access controls.
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Your Rights
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            You have the right to:
          </p>
          <ul className="list-disc pl-6 mb-8 space-y-2 text-gray-600">
            <li>Access and receive a copy of your personal data</li>
            <li>Rectify inaccurate personal data</li>
            <li>Request deletion of your personal data</li>
            <li>Object to processing of your personal data</li>
            <li>Request restriction of processing</li>
            <li>Data portability</li>
          </ul>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Cookies and Tracking
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            We use cookies and similar tracking technologies to track activity on our platform and hold certain information. You can instruct your browser to refuse all cookies or to indicate when a cookie is being sent. However, if you do not accept cookies, you may not be able to use some portions of our service.
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Changes to This Policy
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            We may update our Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page and updating the &quot;Last updated&quot; date at the top of this policy.
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Contact Us
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            If you have any questions about this Privacy Policy, please contact us at privacy@qnt9.com.
          </p>
        </div>
      </section>
    </main>
  )
}

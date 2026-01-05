"use client"

export default function TermsContent() {
  const lastUpdated = "January 1, 2026"

  return (
    <main className="flex-1 pt-14">
      {/* Header */}
      <section className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-6 md:px-8 py-16">
          <h1 className="text-4xl font-semibold text-gray-900 mb-4">
            Terms of Service
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
            Welcome to QNT9. These Terms of Service govern your use of our stock research platform and services. By accessing or using QNT9, you agree to be bound by these terms.
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            1. Acceptance of Terms
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            By creating an account or using our services, you acknowledge that you have read, understood, and agree to be bound by these Terms of Service and our Privacy Policy. If you do not agree to these terms, please do not use our services.
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            2. Description of Service
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            QNT9 provides a stock research platform that includes real-time market data, company information, news feeds, watchlist management, and related analytical tools. Our services are provided for informational purposes only and should not be considered as financial advice.
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            3. User Accounts
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            To access certain features, you must create an account. You agree to:
          </p>
          <ul className="list-disc pl-6 mb-8 space-y-2 text-gray-600">
            <li>Provide accurate and complete information during registration</li>
            <li>Maintain the security of your account credentials</li>
            <li>Notify us immediately of any unauthorized use of your account</li>
            <li>Accept responsibility for all activities that occur under your account</li>
          </ul>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            4. Subscription and Payments
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            Some features require a paid subscription. By subscribing, you agree to pay all applicable fees. Subscriptions automatically renew unless cancelled before the renewal date. Refunds are provided in accordance with our refund policy.
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            5. Acceptable Use
          </h2>
          <p className="text-gray-600 leading-relaxed mb-4">
            You agree not to:
          </p>
          <ul className="list-disc pl-6 mb-8 space-y-2 text-gray-600">
            <li>Use the service for any unlawful purpose</li>
            <li>Attempt to gain unauthorized access to our systems</li>
            <li>Interfere with or disrupt the service</li>
            <li>Reproduce, distribute, or sell any content without permission</li>
            <li>Use automated systems to access the service without our consent</li>
            <li>Violate any applicable laws or regulations</li>
          </ul>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            6. Intellectual Property
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            All content, trademarks, and intellectual property on QNT9 are owned by us or our licensors. You may not use, copy, or distribute any content without our express written permission, except for personal, non-commercial use of the services.
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            7. Disclaimer of Warranties
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            QNT9 is provided &quot;as is&quot; without warranties of any kind, either express or implied. We do not guarantee the accuracy, completeness, or timeliness of any information provided. Market data may be delayed or inaccurate. We are not responsible for any investment decisions made based on our platform.
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            8. Limitation of Liability
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            To the maximum extent permitted by law, QNT9 and its affiliates shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including but not limited to loss of profits, data, or other intangible losses, resulting from your use of the service.
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            9. Termination
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            We reserve the right to suspend or terminate your account at any time for any reason, including violation of these terms. Upon termination, your right to use the service will immediately cease.
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            10. Changes to Terms
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            We may modify these terms at any time. We will notify users of material changes by posting a notice on our platform. Continued use of the service after changes constitutes acceptance of the modified terms.
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            11. Contact Information
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            If you have any questions about these Terms of Service, please contact us at legal@qnt9.com.
          </p>
        </div>
      </section>
    </main>
  )
}

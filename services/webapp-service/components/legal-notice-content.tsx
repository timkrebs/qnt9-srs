"use client"

import Link from "next/link"

export default function LegalNoticeContent() {
  return (
    <main className="flex-1 pt-14">
      {/* Header */}
      <section className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-6 md:px-8 py-16">
          <h1 className="text-4xl font-semibold text-gray-900 mb-4">
            Impressum
          </h1>
          <p className="text-gray-500">
            Legal Notice
          </p>
        </div>
      </section>

      {/* Content */}
      <section className="max-w-4xl mx-auto px-6 md:px-8 py-12">
        <div className="prose prose-gray max-w-none">
          <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">
            Diensteanbieter
          </h2>
          <p className="text-gray-600 leading-relaxed mb-2">Tim Krebs</p>
          <p className="text-gray-600 leading-relaxed mb-2">Fürmoosen 39</p>
          <p className="text-gray-600 leading-relaxed mb-8">85665 Moosach</p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Kontaktmöglichkeiten
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            E-Mail-Adresse:{" "}
            <Link
              href="mailto:timkrebs9@gmail.com"
              className="text-blue-600 hover:text-blue-800 transition-colors"
            >
              timkrebs9@gmail.com
            </Link>
          </p>

          <h2 className="text-2xl font-semibold text-gray-900 mt-12 mb-4">
            Journalistisch-redaktionelle Angebote
          </h2>
          <p className="text-gray-600 leading-relaxed mb-8">
            Inhaltlich verantwortlich: Tim Krebs
          </p>

          <p className="text-sm text-gray-400 mt-16">
            <Link
              href="https://datenschutz-generator.de/"
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="hover:text-gray-600 transition-colors"
            >
              Erstellt mit kostenlosem Datenschutz-Generator.de von Dr. Thomas Schwenke
            </Link>
          </p>
        </div>
      </section>
    </main>
  )
}

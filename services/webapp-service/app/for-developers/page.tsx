import Header from "@/components/header"
import Sidebar from "@/components/sidebar"

export default function ForDevelopersPage() {
  return (
    <div className="min-h-screen bg-white">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 ml-64 pt-14">
          <div className="max-w-5xl mx-auto px-8 py-16">
            <h1 className="text-5xl font-normal mb-6">For Developers</h1>
            <p className="text-base leading-relaxed text-gray-700">
              Build with OpenAI's powerful APIs and developer tools.
            </p>
          </div>
        </main>
      </div>
    </div>
  )
}

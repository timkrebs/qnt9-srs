import Header from "@/components/header"
import Sidebar from "@/components/sidebar"

export default function NewsPage() {
  return (
    <div className="min-h-screen bg-white">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 ml-64 pt-14">
          <div className="max-w-5xl mx-auto px-8 py-16">
            <h1 className="text-5xl font-normal mb-6">News</h1>
            <p className="text-base leading-relaxed text-gray-700">
              Stay updated with the latest announcements and updates from OpenAI.
            </p>
          </div>
        </main>
      </div>
    </div>
  )
}

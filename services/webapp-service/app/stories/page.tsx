import Header from "@/components/header"
import Sidebar from "@/components/sidebar"

export default function StoriesPage() {
  return (
    <div className="min-h-screen bg-white">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 ml-64 pt-14">
          <div className="max-w-5xl mx-auto px-8 py-16">
            <h1 className="text-5xl font-normal mb-6">Stories</h1>
            <p className="text-base leading-relaxed text-gray-700">
              Discover how people are using OpenAI's technology.
            </p>
          </div>
        </main>
      </div>
    </div>
  )
}

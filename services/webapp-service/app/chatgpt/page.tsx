import Header from "@/components/header"
import Sidebar from "@/components/sidebar"

export default function ChatGPTPage() {
  return (
    <div className="min-h-screen bg-white">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 md:ml-64 pt-14">
          <div className="max-w-5xl mx-auto px-4 md:px-8 py-8 md:py-16">
            <h1 className="text-3xl md:text-4xl lg:text-5xl font-normal mb-4 md:mb-6">ChatGPT</h1>
            <p className="text-base leading-relaxed text-gray-700">Explore ChatGPT, our conversational AI assistant.</p>
          </div>
        </main>
      </div>
    </div>
  )
}

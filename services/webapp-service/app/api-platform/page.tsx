import Header from "@/components/header"
import Sidebar from "@/components/sidebar"
import ApiPlatformContent from "@/components/api-platform-content"

export default function ApiPlatformPage() {
  return (
    <div className="min-h-screen bg-white">
      <Header />
      <div className="flex">
        <Sidebar />
        <ApiPlatformContent />
      </div>
    </div>
  )
}

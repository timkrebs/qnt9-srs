import Header from "@/components/header"
import Sidebar from "@/components/sidebar"
import AgentsContent from "@/components/agents-content"

export default function AgentsPage() {
  return (
    <div className="min-h-screen bg-white">
      <Header />
      <div className="flex">
        <Sidebar />
        <AgentsContent />
      </div>
    </div>
  )
}

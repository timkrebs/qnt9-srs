import Header from "@/components/header"
import Footer from "@/components/footer"
import DocsContent from "@/components/docs-content"

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Header />
      <DocsContent />
      <Footer />
    </div>
  )
}

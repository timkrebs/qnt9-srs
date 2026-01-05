import Header from "@/components/header"
import Footer from "@/components/footer"
import TermsContent from "@/components/terms-content"

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Header />
      <TermsContent />
      <Footer />
    </div>
  )
}

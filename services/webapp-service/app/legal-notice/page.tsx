import Header from "@/components/header"
import Footer from "@/components/footer"
import LegalNoticeContent from "@/components/legal-notice-content"

export default function LegalNoticePage() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Header />
      <LegalNoticeContent />
      <Footer />
    </div>
  )
}

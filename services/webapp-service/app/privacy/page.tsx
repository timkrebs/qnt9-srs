import Header from "@/components/header"
import Footer from "@/components/footer"
import PrivacyContent from "@/components/privacy-content"

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Header />
      <PrivacyContent />
      <Footer />
    </div>
  )
}

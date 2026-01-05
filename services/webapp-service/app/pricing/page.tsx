import Header from "@/components/header"
import Footer from "@/components/footer"
import PricingContent from "@/components/pricing-content"

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Header />
      <PricingContent />
      <Footer />
    </div>
  )
}

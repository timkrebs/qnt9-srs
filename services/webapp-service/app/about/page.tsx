import Header from "@/components/header"
import Footer from "@/components/footer"
import AboutContent from "@/components/about-content"

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Header />
      <AboutContent />
      <Footer />
    </div>
  )
}

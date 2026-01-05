import { Suspense } from "react"
import Header from "@/components/header"
import SearchContent from "@/components/search-content"

function SearchPageContent() {
  return (
    <div className="min-h-screen bg-white">
      <Header />
      <SearchContent />
    </div>
  )
}

export default function SearchPage() {
  return (
    <Suspense fallback={null}>
      <SearchPageContent />
    </Suspense>
  )
}

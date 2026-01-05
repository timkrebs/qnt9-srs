import { ArrowUpRight } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function ApiPlatformContent() {
  const companies = [
    { name: "Lowe's", logo: "LOWE'S" },
    { name: "Morgan Stanley", logo: "Morgan Stanley" },
    { name: "Booking.com", logo: "Booking.com" },
    { name: "AMGEN", logo: "AMGEN" },
    { name: "Mercado Libre", logo: "mercado libre" },
  ]

  const models = [
    {
      name: "GPT-5.2",
      inputPrice: "$1.75 per 1M tokens",
      outputPrice: "$14.00 per 1M tokens",
      contextLength: "400K context length",
      maxTokens: "128K max output tokens",
      cutoffDate: "Aug 31, 2025",
      gradient: "from-pink-300 via-orange-200 to-blue-300",
    },
    {
      name: "GPT-5.2 pro",
      inputPrice: "$21.00 per 1M tokens",
      outputPrice: "$168.00 per 1M tokens",
      contextLength: "400K context length",
      maxTokens: "128K max output tokens",
      cutoffDate: "Aug 31, 2025",
      gradient: "from-blue-200 via-pink-200 to-orange-200",
    },
    {
      name: "GPT-5 mini",
      inputPrice: "$0.25 per 1M tokens",
      outputPrice: "$2.00 per 1M tokens",
      contextLength: "400K context length",
      maxTokens: "128K max output tokens",
      cutoffDate: "Sep 30, 2024",
      gradient: "from-pink-300 via-purple-200 to-blue-300",
    },
  ]

  return (
    <main className="ml-64 pt-14 flex-1">
      <div className="max-w-6xl mx-auto px-8 py-16">
        {/* Hero Section */}
        <section className="text-center mb-20">
          <h1 className="text-6xl font-normal mb-8 tracking-tight">
            Build leading AI products
            <br />
            on OpenAI's platform
          </h1>
          <div className="flex items-center justify-center gap-4">
            <Button className="bg-black text-white hover:bg-gray-800 rounded-full px-6 h-11">Contact sales</Button>
            <Button
              variant="ghost"
              className="text-black hover:bg-gray-100 rounded-full px-6 h-11 flex items-center gap-1"
            >
              Start building
              <ArrowUpRight className="w-4 h-4" />
            </Button>
          </div>
        </section>

        {/* Company Logos */}
        <section className="mb-32">
          <div className="flex items-center justify-between max-w-5xl mx-auto">
            {companies.map((company, index) => (
              <div key={index} className="text-black font-medium text-lg">
                {company.logo}
              </div>
            ))}
          </div>
        </section>

        {/* Powered by Models Section */}
        <section className="mb-20">
          <div className="text-center mb-12">
            <h2 className="text-5xl font-normal mb-6 tracking-tight">Powered by our frontier models</h2>
            <p className="text-gray-700 max-w-2xl mx-auto text-lg">
              Our industry-leading models are designed for real-world utility,
              <br />
              delivering advanced intelligence and multimodal capabilities.
            </p>
          </div>

          {/* Model Cards */}
          <div className="grid grid-cols-3 gap-6 mt-16">
            {models.map((model, index) => (
              <div
                key={index}
                className={`bg-gradient-to-br ${model.gradient} rounded-2xl p-8 min-h-[380px] flex flex-col justify-between`}
              >
                <div>
                  <h3 className="text-3xl font-normal mb-6 text-black">{model.name}</h3>
                  <div className="space-y-2 text-sm text-gray-800">
                    <p>Input: {model.inputPrice}</p>
                    <p>Output: {model.outputPrice}</p>
                  </div>
                  <div className="mt-6 space-y-1 text-sm text-gray-800">
                    <p>{model.contextLength}</p>
                    <p>{model.maxTokens}</p>
                  </div>
                </div>
                <div className="text-sm text-gray-800 mt-6">Knowledge cut-off: {model.cutoffDate}</div>
              </div>
            ))}
          </div>
        </section>

        {/* CTA Section */}
        <section className="text-center py-20">
          <h2 className="text-4xl font-normal mb-8 tracking-tight">Start working with GPT-5</h2>
          <Button variant="ghost" className="text-black hover:bg-gray-100 rounded-full px-6 h-11">
            Start building
          </Button>
        </section>
      </div>
    </main>
  )
}

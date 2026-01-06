import { ArrowUpRight } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function AgentsContent() {
  const testimonials = [
    {
      company: "ramp",
      logo: "ramp ↗",
      quote:
        "Agent Builder transformed what took months of orchestration, custom code, and manual optimization into hours—getting an agent live in two sprints instead of two quarters.",
      metric: "70%",
      metricLabel: "reduction in iteration cycles",
    },
    {
      company: "RIPPLING",
      logo: "RIPPLING",
      metric: "40%",
      metricLabel: "faster agent evaluation timelines",
    },
    {
      company: "Canva",
      logo: "Canva",
      metric: "2 weeks",
      metricLabel: "of custom front-end UI work saved when building an agent",
    },
    {
      company: "CARLYLE",
      logo: "CARLYLE",
      metric: "30%",
      metricLabel: "increased agent accuracy with evals",
    },
    {
      company: "box",
      logo: "box",
      metric: "75%",
      metricLabel: "less time to develop agentic workflows",
    },
  ]

  return (
    <main className="md:ml-64 pt-14 flex-1">
      <div className="max-w-7xl mx-auto px-4 md:px-8 py-8 md:py-16">
        {/* Hero Section */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-16 mb-16 md:mb-32 items-center">
          <div>
            <h1 className="text-3xl md:text-5xl lg:text-6xl font-normal mb-6 md:mb-8 leading-tight tracking-tight">
              Build every step of agents on one platform
            </h1>
            <p className="text-gray-700 text-base md:text-lg mb-6 md:mb-8">
              Ship production-ready agents faster and more reliably across your products
              <br className="hidden md:block" />
              <span className="md:hidden"> </span>and organization.
            </p>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 md:gap-4">
              <Button variant="ghost" className="bg-gray-100 text-black hover:bg-gray-200 rounded-full px-6 h-11">
                Contact sales
              </Button>
              <Button
                variant="ghost"
                className="text-black hover:bg-gray-100 rounded-full px-6 h-11 flex items-center gap-1"
              >
                Start building
                <ArrowUpRight className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Hero Visual */}
          <div className="relative">
            <div className="bg-gradient-to-br from-blue-300 via-purple-200 to-orange-200 rounded-3xl h-[450px] flex items-center justify-center relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-t from-orange-100/30 to-blue-200/30" />
              <div className="relative flex items-center gap-4">
                <div className="bg-white rounded-full px-8 py-4 shadow-lg flex items-center gap-3">
                  <div className="w-8 h-8 bg-green-400 rounded-full flex items-center justify-center">
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="black">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  </div>
                  <span className="text-xl font-medium">Start</span>
                </div>
                <div className="bg-white rounded-3xl px-8 py-4 shadow-lg">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 bg-blue-300 rounded-lg flex items-center justify-center">
                      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="black" strokeWidth="2">
                        <path d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z" />
                      </svg>
                    </div>
                    <div>
                      <div className="text-xl font-medium mb-1">Categorize</div>
                      <div className="text-gray-600 text-sm">Agent</div>
                    </div>
                  </div>
                </div>
                <div className="bg-white rounded-full w-16 h-16 shadow-lg flex items-center justify-center">
                  <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="black" strokeWidth="2">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M12 1v6m0 6v6M1 12h6m6 0h6m6 0h6" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Testimonials Section */}
        <section>
          <h2 className="text-2xl md:text-4xl lg:text-5xl font-normal text-center mb-8 md:mb-16 tracking-tight">
            Leading organizations build agents with OpenAI
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
            {testimonials.slice(0, 3).map((item, index) => (
              <div
                key={index}
                className={`bg-gray-50 rounded-2xl p-8 ${
                  index === 0 ? "col-span-2 row-span-2" : ""
                } min-h-[240px] flex flex-col justify-between`}
              >
                <div>
                  <div className="text-xl font-medium mb-6">{item.logo}</div>
                  {item.quote && <p className="text-gray-800 mb-8 text-lg leading-relaxed">{item.quote}</p>}
                </div>
                <div>
                  <div className="text-4xl font-normal mb-2">{item.metric}</div>
                  <div className="text-sm text-gray-600">{item.metricLabel}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-6 mt-6">
            {testimonials.slice(3).map((item, index) => (
              <div key={index} className="bg-gray-50 rounded-2xl p-8 min-h-[240px] flex flex-col justify-between">
                <div className="text-xl font-medium mb-6">{item.logo}</div>
                <div>
                  <div className="text-4xl font-normal mb-2">{item.metric}</div>
                  <div className="text-sm text-gray-600">{item.metricLabel}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  )
}

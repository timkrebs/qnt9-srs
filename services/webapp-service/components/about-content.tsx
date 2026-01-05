"use client"

import Link from "next/link"
import Image from "next/image"
import { ArrowRight, Users, Target, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"

const VALUES = [
  {
    icon: <Target className="w-6 h-6" />,
    title: "Mission-Driven",
    description: "We are building tools that democratize access to financial data and empower individual investors.",
  },
  {
    icon: <Users className="w-6 h-6" />,
    title: "User-First",
    description: "Every feature we build starts with understanding what our users need to make better investment decisions.",
  },
  {
    icon: <Zap className="w-6 h-6" />,
    title: "Innovation",
    description: "We leverage cutting-edge technology to deliver real-time data and insights faster than ever before.",
  },
]

const TEAM = [
  { name: "Alex Chen", role: "Founder & CEO", initials: "AC" },
  { name: "Sarah Miller", role: "Head of Product", initials: "SM" },
  { name: "James Wilson", role: "Lead Engineer", initials: "JW" },
  { name: "Emily Zhang", role: "Head of Data", initials: "EZ" },
]

export default function AboutContent() {
  return (
    <main className="flex-1 pt-14">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-b from-gray-50 to-white overflow-hidden">
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-20">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h1 className="text-4xl md:text-5xl font-semibold text-gray-900 mb-6 tracking-tight">
                Empowering investors with data
              </h1>
              <p className="text-xl text-gray-600 mb-8 leading-relaxed">
                QNT9 is a stock research platform built for individual investors who want professional-grade market data without the enterprise price tag.
              </p>
              <div className="flex items-center gap-4">
                <Link href="/signup">
                  <Button className="bg-gray-900 text-white hover:bg-gray-800 px-6">
                    Get Started
                  </Button>
                </Link>
                <Link href="/pricing">
                  <Button variant="ghost" className="text-gray-600 hover:text-gray-900">
                    View Pricing
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                </Link>
              </div>
            </div>
            <div className="relative aspect-square max-w-md mx-auto lg:mx-0">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-100 via-purple-50 to-pink-100 rounded-3xl" />
              <div className="absolute inset-4 bg-white rounded-2xl shadow-sm flex items-center justify-center">
                <span className="text-6xl font-bold text-gray-900">QNT9</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Mission Section */}
      <section className="bg-white border-y border-gray-100">
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-20">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-3xl font-semibold text-gray-900 mb-6">
              Our Mission
            </h2>
            <p className="text-xl text-gray-600 leading-relaxed">
              We believe everyone deserves access to the same quality of market data that institutional investors have. Our mission is to level the playing field by providing powerful, easy-to-use research tools for individual investors.
            </p>
          </div>
        </div>
      </section>

      {/* Values Section */}
      <section className="bg-gray-50">
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-20">
          <h2 className="text-2xl font-semibold text-gray-900 mb-12 text-center">
            Our Values
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {VALUES.map((value) => (
              <div
                key={value.title}
                className="bg-white rounded-xl border border-gray-100 p-8 hover:border-gray-200 hover:shadow-sm transition-all"
              >
                <div className="w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center text-gray-700 mb-6">
                  {value.icon}
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">
                  {value.title}
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  {value.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Team Section */}
      <section className="bg-white">
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-20">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4 text-center">
            Our Team
          </h2>
          <p className="text-gray-600 text-center mb-12 max-w-2xl mx-auto">
            A small team of engineers and financial experts passionate about making investing accessible.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {TEAM.map((member) => (
              <div key={member.name} className="text-center">
                <div className="w-20 h-20 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
                  <span className="text-xl font-semibold text-gray-600">
                    {member.initials}
                  </span>
                </div>
                <h3 className="font-semibold text-gray-900">{member.name}</h3>
                <p className="text-sm text-gray-500">{member.role}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-gray-900">
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-20 text-center">
          <h2 className="text-3xl font-semibold text-white mb-4">
            Ready to start your research?
          </h2>
          <p className="text-gray-400 mb-8 max-w-xl mx-auto">
            Join thousands of investors using QNT9 to make better investment decisions.
          </p>
          <Link href="/signup">
            <Button className="bg-white text-gray-900 hover:bg-gray-100 px-8">
              Create Free Account
            </Button>
          </Link>
        </div>
      </section>
    </main>
  )
}

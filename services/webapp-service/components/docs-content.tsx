"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Book, Code, Zap, Shield, FileText, ExternalLink, ChevronRight, Loader2 } from "lucide-react"
import { blogService, type BlogPost } from "@/lib/api/blog"
import { cn } from "@/lib/utils"

interface DocCategory {
  icon: React.ReactNode
  title: string
  description: string
  articles: { title: string; href: string }[]
}

const DOC_CATEGORIES: DocCategory[] = [
  {
    icon: <Book className="w-6 h-6" />,
    title: "Getting Started",
    description: "Learn the basics of using finio for stock research.",
    articles: [
      { title: "Quick Start Guide", href: "/docs" },
      { title: "Creating Your Account", href: "/docs" },
      { title: "Understanding the Dashboard", href: "/docs" },
      { title: "Your First Watchlist", href: "/docs" },
    ],
  },
  {
    icon: <Code className="w-6 h-6" />,
    title: "API Reference",
    description: "Integrate finio data into your applications.",
    articles: [
      { title: "Authentication", href: "/docs" },
      { title: "Stock Quotes Endpoint", href: "/docs" },
      { title: "Company Details API", href: "/docs" },
      { title: "Historical Data", href: "/docs" },
    ],
  },
  {
    icon: <Zap className="w-6 h-6" />,
    title: "Features",
    description: "Deep dive into platform capabilities.",
    articles: [
      { title: "Real-Time Quotes", href: "/docs" },
      { title: "Price Alerts", href: "/docs" },
      { title: "Watchlist Management", href: "/docs" },
      { title: "News Feed", href: "/docs" },
    ],
  },
  {
    icon: <Shield className="w-6 h-6" />,
    title: "Security",
    description: "How we protect your data and privacy.",
    articles: [
      { title: "Data Encryption", href: "/docs" },
      { title: "Account Security", href: "/docs" },
      { title: "Two-Factor Authentication", href: "/docs" },
      { title: "Privacy Practices", href: "/docs" },
    ],
  },
]

// Fallback blog posts for when Supabase is not configured or fails to load
const FALLBACK_BLOG_POSTS: BlogPost[] = [
  {
    id: "1",
    title: "Introducing Real-Time WebSocket Quotes",
    slug: "introducing-realtime-websocket-quotes",
    excerpt: "We are excited to announce real-time streaming quotes for all Pro subscribers, enabling sub-second price updates for your watchlist.",
    content: "",
    category: "Product",
    author_id: null,
    author_name: "finio Team",
    image_url: null,
    published: true,
    featured: true,
    published_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "2",
    title: "Understanding Market Cap and Valuation",
    slug: "understanding-market-cap-valuation",
    excerpt: "A comprehensive guide to understanding market capitalization and how it relates to company valuation and investment decisions.",
    content: "",
    category: "Education",
    author_id: null,
    author_name: "finio Team",
    image_url: null,
    published: true,
    featured: false,
    published_at: new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "3",
    title: "New API Rate Limits and Best Practices",
    slug: "api-rate-limits-best-practices",
    excerpt: "Learn about our updated API rate limits and best practices for efficient data retrieval in your applications.",
    content: "",
    category: "API",
    author_id: null,
    author_name: "finio Team",
    image_url: null,
    published: true,
    featured: false,
    published_at: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
]

export default function DocsContent() {
  const [blogPosts, setBlogPosts] = useState<BlogPost[]>(FALLBACK_BLOG_POSTS)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const loadBlogPosts = async () => {
      try {
        const posts = await blogService.getPublishedPosts()
        if (posts.length > 0) {
          setBlogPosts(posts.slice(0, 6)) // Show up to 6 posts
        }
      } catch (error) {
        console.error("Error loading blog posts:", error)
        // Keep fallback posts on error
      } finally {
        setIsLoading(false)
      }
    }

    loadBlogPosts()
  }, [])
  return (
    <main className="flex-1 pt-14">
      {/* Hero Section */}
      <section className="bg-gradient-to-b from-gray-50 to-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-16">
          <div className="max-w-2xl">
            <h1 className="text-4xl font-semibold text-gray-900 mb-4">
              Documentation
            </h1>
            <p className="text-xl text-gray-600">
              Learn how to use finio for stock research, integrate our API, and make the most of the platform.
            </p>
          </div>
        </div>
      </section>

      {/* Documentation Categories */}
      <section className="max-w-6xl mx-auto px-6 md:px-8 py-16">
        <h2 className="text-2xl font-semibold text-gray-900 mb-8">
          Browse by Category
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {DOC_CATEGORIES.map((category) => (
            <div
              key={category.title}
              className="rounded-xl border border-gray-100 bg-white hover:border-gray-200 hover:shadow-sm transition-all overflow-hidden"
            >
              <div className="p-6 border-b border-gray-100">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center text-gray-700">
                    {category.icon}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-1">
                      {category.title}
                    </h3>
                    <p className="text-sm text-gray-500">
                      {category.description}
                    </p>
                  </div>
                </div>
              </div>
              <div className="p-2">
                {category.articles.map((article) => (
                  <Link
                    key={article.title}
                    href={article.href}
                    className="flex items-center justify-between px-4 py-3 rounded-lg hover:bg-gray-50 transition-colors group"
                  >
                    <span className="text-sm text-gray-700 group-hover:text-gray-900">
                      {article.title}
                    </span>
                    <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600" />
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Blog / Updates Section */}
      <section className="bg-gray-50 border-t border-gray-100">
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-16">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-2xl font-semibold text-gray-900">
              Latest Updates
            </h2>
            {isLoading && (
              <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {blogPosts.slice(0, 3).map((post) => (
              <Link
                key={post.id}
                href={`/blog/${post.slug}`}
                className="group block"
              >
                <article className="h-full bg-white rounded-xl border border-gray-100 p-6 hover:border-gray-200 hover:shadow-sm transition-all">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-600">
                      {post.category}
                    </span>
                    <span className="text-xs text-gray-400">
                      {post.published_at
                        ? new Date(post.published_at).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          })
                        : "Draft"}
                    </span>
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-2 group-hover:text-gray-700 transition-colors">
                    {post.title}
                  </h3>
                  <p className="text-sm text-gray-500 line-clamp-3">
                    {post.excerpt}
                  </p>
                  <div className="mt-4 flex items-center text-sm text-gray-600 group-hover:text-gray-900 transition-colors">
                    Read more
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </div>
                </article>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-white border-t border-gray-100">
        <div className="max-w-6xl mx-auto px-6 md:px-8 py-16">
          <div className="bg-gray-900 rounded-2xl p-8 md:p-12 flex flex-col md:flex-row items-center justify-between gap-6">
            <div>
              <h2 className="text-2xl font-semibold text-white mb-2">
                Need help getting started?
              </h2>
              <p className="text-gray-400">
                Contact our support team for personalized assistance.
              </p>
            </div>
            <Link
              href="/about"
              className="shrink-0 inline-flex items-center gap-2 px-6 py-3 rounded-full bg-white text-gray-900 font-medium hover:bg-gray-100 transition-colors"
            >
              Contact Support
              <ExternalLink className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>
    </main>
  )
}

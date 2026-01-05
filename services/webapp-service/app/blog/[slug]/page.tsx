'use client'

import { useState, useEffect, use } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Header from '@/components/header'
import Footer from '@/components/footer'
import { blogService, type BlogPost } from '@/lib/api/blog'
import { ArrowLeft, Calendar, User, Tag } from 'lucide-react'
import Link from 'next/link'

interface BlogPostPageProps {
  params: Promise<{ slug: string }>
}

export default function BlogPostPage({ params }: BlogPostPageProps) {
  const { slug } = use(params)
  const [post, setPost] = useState<BlogPost | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadPost = async () => {
      try {
        setIsLoading(true)
        const data = await blogService.getPostBySlug(slug)
        if (!data) {
          setError('Post not found')
        } else {
          setPost(data)
        }
      } catch (err) {
        console.error('Error loading post:', err)
        setError('Failed to load blog post')
      } finally {
        setIsLoading(false)
      }
    }

    loadPost()
  }, [slug])

  if (isLoading) {
    return (
      <div className="flex min-h-screen flex-col bg-black">
        <Header />
        <main className="flex flex-1 items-center justify-center">
          <p className="text-zinc-400">Loading...</p>
        </main>
        <Footer />
      </div>
    )
  }

  if (error || !post) {
    return (
      <div className="flex min-h-screen flex-col bg-black">
        <Header />
        <main className="flex flex-1 items-center justify-center">
          <div className="text-center">
            <h1 className="mb-4 text-2xl font-bold text-white">
              {error || 'Post not found'}
            </h1>
            <Link
              href="/docs"
              className="inline-flex items-center text-zinc-400 hover:text-white"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Documentation
            </Link>
          </div>
        </main>
        <Footer />
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col bg-black">
      <Header />
      <main className="flex-1 py-12">
        <article className="mx-auto max-w-3xl px-6 md:px-8">
          {/* Back Link */}
          <Link
            href="/docs"
            className="mb-8 inline-flex items-center text-zinc-400 hover:text-white"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Documentation
          </Link>

          {/* Cover Image */}
          {post.image_url && (
            <div className="mb-8 overflow-hidden rounded-lg">
              <img
                src={post.image_url}
                alt={post.title}
                className="h-64 w-full object-cover"
              />
            </div>
          )}

          {/* Post Header */}
          <header className="mb-8">
            <div className="mb-4 flex items-center gap-3">
              <span className="rounded-full bg-zinc-800 px-3 py-1 text-sm text-zinc-300">
                <Tag className="mr-1 inline h-3 w-3" />
                {post.category}
              </span>
            </div>

            <h1 className="mb-4 text-4xl font-bold text-white">{post.title}</h1>

            <div className="flex items-center gap-4 text-sm text-zinc-400">
              {post.author_name && (
                <span className="flex items-center gap-1">
                  <User className="h-4 w-4" />
                  {post.author_name}
                </span>
              )}
              {post.published_at && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-4 w-4" />
                  {new Date(post.published_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </span>
              )}
            </div>
          </header>

          {/* Post Content */}
          <div className="prose prose-invert prose-zinc max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ children }) => (
                  <h1 className="mb-6 mt-10 text-3xl font-bold text-white">{children}</h1>
                ),
                h2: ({ children }) => (
                  <h2 className="mb-4 mt-8 text-2xl font-semibold text-white">{children}</h2>
                ),
                h3: ({ children }) => (
                  <h3 className="mb-3 mt-6 text-xl font-semibold text-white">{children}</h3>
                ),
                p: ({ children }) => (
                  <p className="mb-4 leading-relaxed text-zinc-300">{children}</p>
                ),
                a: ({ href, children }) => (
                  <a
                    href={href}
                    className="text-blue-400 underline hover:text-blue-300"
                    target={href?.startsWith('http') ? '_blank' : undefined}
                    rel={href?.startsWith('http') ? 'noopener noreferrer' : undefined}
                  >
                    {children}
                  </a>
                ),
                ul: ({ children }) => (
                  <ul className="mb-4 list-disc space-y-2 pl-6 text-zinc-300">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="mb-4 list-decimal space-y-2 pl-6 text-zinc-300">{children}</ol>
                ),
                li: ({ children }) => <li className="text-zinc-300">{children}</li>,
                blockquote: ({ children }) => (
                  <blockquote className="my-4 border-l-4 border-zinc-700 pl-4 italic text-zinc-400">
                    {children}
                  </blockquote>
                ),
                code: ({ className, children }) => {
                  const isInline = !className
                  if (isInline) {
                    return (
                      <code className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-sm text-zinc-200">
                        {children}
                      </code>
                    )
                  }
                  return (
                    <code className="block overflow-x-auto rounded-lg bg-zinc-900 p-4 font-mono text-sm text-zinc-200">
                      {children}
                    </code>
                  )
                },
                pre: ({ children }) => (
                  <pre className="my-4 overflow-x-auto rounded-lg bg-zinc-900 p-4">
                    {children}
                  </pre>
                ),
                table: ({ children }) => (
                  <div className="my-4 overflow-x-auto">
                    <table className="w-full border-collapse border border-zinc-700">
                      {children}
                    </table>
                  </div>
                ),
                th: ({ children }) => (
                  <th className="border border-zinc-700 bg-zinc-800 px-4 py-2 text-left font-semibold text-white">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="border border-zinc-700 px-4 py-2 text-zinc-300">{children}</td>
                ),
                hr: () => <hr className="my-8 border-zinc-800" />,
                strong: ({ children }) => (
                  <strong className="font-semibold text-white">{children}</strong>
                ),
                em: ({ children }) => <em className="italic">{children}</em>,
              }}
            >
              {post.content}
            </ReactMarkdown>
          </div>
        </article>
      </main>
      <Footer />
    </div>
  )
}

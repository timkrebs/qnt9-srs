'use client'

import { useState, useEffect } from 'react'
import dynamic from 'next/dynamic'
import Header from '@/components/header'
import Footer from '@/components/footer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { blogService, type BlogPost, type BlogPostInput } from '@/lib/api/blog'
import { isSupabaseConfigured } from '@/lib/supabase'
import { useAuth } from '@/lib/auth/auth-context'
import { Plus, Edit, Trash2, Eye, EyeOff, Star, ArrowLeft, AlertCircle } from 'lucide-react'
import '@uiw/react-md-editor/markdown-editor.css'
import '@uiw/react-markdown-preview/markdown.css'

// Dynamic import to avoid SSR issues with the markdown editor
const MDEditor = dynamic(() => import('@uiw/react-md-editor'), { ssr: false })

const CATEGORIES = ['Product', 'Education', 'API', 'Company', 'General']

export default function AdminBlogPage() {
  const { isAuthenticated, isLoading: authLoading, canManageBlog, isAdmin } = useAuth()
  const [posts, setPosts] = useState<BlogPost[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [editingPost, setEditingPost] = useState<BlogPost | null>(null)
  
  // Form state
  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [excerpt, setExcerpt] = useState('')
  const [content, setContent] = useState('')
  const [category, setCategory] = useState('General')
  const [authorName, setAuthorName] = useState('QNT9 Team')
  const [imageUrl, setImageUrl] = useState('')
  const [published, setPublished] = useState(false)
  const [featured, setFeatured] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (!authLoading && isAuthenticated && canManageBlog) {
      loadPosts()
    }
  }, [authLoading, isAuthenticated, canManageBlog])

  const loadPosts = async () => {
    try {
      setIsLoading(true)
      const data = await blogService.getAllPosts()
      setPosts(data)
      setError(null)
    } catch (err) {
      console.error('Error loading posts:', err)
      setError('Failed to load blog posts')
    } finally {
      setIsLoading(false)
    }
  }

  const resetForm = () => {
    setTitle('')
    setSlug('')
    setExcerpt('')
    setContent('')
    setCategory('General')
    setAuthorName('QNT9 Team')
    setImageUrl('')
    setPublished(false)
    setFeatured(false)
    setEditingPost(null)
  }

  const handleNew = () => {
    resetForm()
    setIsEditing(true)
  }

  const handleEdit = (post: BlogPost) => {
    setEditingPost(post)
    setTitle(post.title)
    setSlug(post.slug)
    setExcerpt(post.excerpt || '')
    setContent(post.content)
    setCategory(post.category)
    setAuthorName(post.author_name || 'QNT9 Team')
    setImageUrl(post.image_url || '')
    setPublished(post.published)
    setFeatured(post.featured)
    setIsEditing(true)
  }

  const handleTitleChange = (newTitle: string) => {
    setTitle(newTitle)
    if (!editingPost) {
      setSlug(blogService.generateSlug(newTitle))
    }
  }

  const handleSave = async () => {
    if (!title || !slug || !content) {
      setError('Title, slug, and content are required')
      return
    }

    try {
      setIsSaving(true)
      setError(null)

      const postData: BlogPostInput = {
        title,
        slug,
        excerpt: excerpt || undefined,
        content,
        category,
        author_name: authorName,
        image_url: imageUrl || undefined,
        published,
        featured,
      }

      if (editingPost) {
        await blogService.updatePost(editingPost.id, postData)
      } else {
        await blogService.createPost(postData)
      }

      await loadPosts()
      setIsEditing(false)
      resetForm()
    } catch (err) {
      console.error('Error saving post:', err)
      setError('Failed to save blog post')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this post?')) {
      return
    }

    try {
      await blogService.deletePost(id)
      await loadPosts()
    } catch (err) {
      console.error('Error deleting post:', err)
      setError('Failed to delete blog post')
    }
  }

  const handleTogglePublished = async (post: BlogPost) => {
    try {
      await blogService.updatePost(post.id, { published: !post.published })
      await loadPosts()
    } catch (err) {
      console.error('Error toggling published status:', err)
      setError('Failed to update post')
    }
  }

  if (authLoading) {
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

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen flex-col bg-black">
        <Header />
        <main className="flex flex-1 items-center justify-center pt-24">
          <div className="text-center">
            <h1 className="mb-4 text-2xl font-bold text-white">Access Denied</h1>
            <p className="text-zinc-400">You must be logged in to access the admin area.</p>
          </div>
        </main>
        <Footer />
      </div>
    )
  }

  if (!canManageBlog) {
    return (
      <div className="flex min-h-screen flex-col bg-black">
        <Header />
        <main className="flex flex-1 items-center justify-center pt-24">
          <div className="text-center">
            <AlertCircle className="mx-auto mb-4 h-12 w-12 text-red-400" />
            <h1 className="mb-4 text-2xl font-bold text-white">Access Denied</h1>
            <p className="text-zinc-400">You do not have permission to manage blog posts.</p>
            <p className="mt-2 text-sm text-zinc-500">Only administrators and editors can access this area.</p>
          </div>
        </main>
        <Footer />
      </div>
    )
  }

  if (isEditing) {
    return (
      <div className="flex min-h-screen flex-col bg-black">
        <Header />
        <main className="flex-1 pt-24 pb-8">
          <div className="mx-auto max-w-6xl px-6 md:px-8">
            <div className="mb-6 flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setIsEditing(false)
                  resetForm()
                }}
                className="text-zinc-400 hover:text-white"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Posts
              </Button>
            </div>

            <h1 className="mb-8 text-3xl font-bold text-white">
              {editingPost ? 'Edit Post' : 'New Post'}
            </h1>

            {error && (
              <div className="mb-6 rounded-lg bg-red-500/10 p-4 text-red-400">
                {error}
              </div>
            )}

            <div className="space-y-6">
              {/* Title */}
              <div>
                <Label htmlFor="title" className="text-zinc-300">
                  Title
                </Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => handleTitleChange(e.target.value)}
                  placeholder="Enter post title"
                  className="mt-2 border-zinc-800 bg-zinc-900 text-white"
                />
              </div>

              {/* Slug */}
              <div>
                <Label htmlFor="slug" className="text-zinc-300">
                  Slug
                </Label>
                <Input
                  id="slug"
                  value={slug}
                  onChange={(e) => setSlug(e.target.value)}
                  placeholder="url-friendly-slug"
                  className="mt-2 border-zinc-800 bg-zinc-900 text-white"
                />
              </div>

              {/* Excerpt */}
              <div>
                <Label htmlFor="excerpt" className="text-zinc-300">
                  Excerpt
                </Label>
                <Input
                  id="excerpt"
                  value={excerpt}
                  onChange={(e) => setExcerpt(e.target.value)}
                  placeholder="Brief description for previews"
                  className="mt-2 border-zinc-800 bg-zinc-900 text-white"
                />
              </div>

              {/* Category and Author */}
              <div className="grid gap-6 md:grid-cols-2">
                <div>
                  <Label htmlFor="category" className="text-zinc-300">
                    Category
                  </Label>
                  <Select value={category} onValueChange={setCategory}>
                    <SelectTrigger className="mt-2 border-zinc-800 bg-zinc-900 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map((cat) => (
                        <SelectItem key={cat} value={cat}>
                          {cat}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="authorName" className="text-zinc-300">
                    Author Name
                  </Label>
                  <Input
                    id="authorName"
                    value={authorName}
                    onChange={(e) => setAuthorName(e.target.value)}
                    placeholder="Author name"
                    className="mt-2 border-zinc-800 bg-zinc-900 text-white"
                  />
                </div>
              </div>

              {/* Image URL */}
              <div>
                <Label htmlFor="imageUrl" className="text-zinc-300">
                  Cover Image URL (optional)
                </Label>
                <Input
                  id="imageUrl"
                  value={imageUrl}
                  onChange={(e) => setImageUrl(e.target.value)}
                  placeholder="https://example.com/image.jpg"
                  className="mt-2 border-zinc-800 bg-zinc-900 text-white"
                />
              </div>

              {/* Toggles */}
              <div className="flex gap-8">
                <div className="flex items-center gap-3">
                  <Switch
                    id="published"
                    checked={published}
                    onCheckedChange={setPublished}
                  />
                  <Label htmlFor="published" className="text-zinc-300">
                    Published
                  </Label>
                </div>

                <div className="flex items-center gap-3">
                  <Switch
                    id="featured"
                    checked={featured}
                    onCheckedChange={setFeatured}
                  />
                  <Label htmlFor="featured" className="text-zinc-300">
                    Featured
                  </Label>
                </div>
              </div>

              {/* Markdown Editor */}
              <div>
                <Label className="text-zinc-300">Content (Markdown)</Label>
                <div className="mt-2" data-color-mode="dark">
                  <MDEditor
                    value={content}
                    onChange={(val) => setContent(val || '')}
                    height={500}
                    preview="edit"
                  />
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-4">
                <Button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="bg-white text-black hover:bg-zinc-200"
                >
                  {isSaving ? 'Saving...' : editingPost ? 'Update Post' : 'Create Post'}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setIsEditing(false)
                    resetForm()
                  }}
                  className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col bg-black">
      <Header />
      <main className="flex-1 pt-24 pb-8">
        <div className="mx-auto max-w-6xl px-6 md:px-8">
          <div className="mb-8 flex items-center justify-between">
            <h1 className="text-3xl font-bold text-white">Blog Admin</h1>
            <Button onClick={handleNew} disabled={!isSupabaseConfigured} className="bg-white text-black hover:bg-zinc-200 disabled:opacity-50">
              <Plus className="mr-2 h-4 w-4" />
              New Post
            </Button>
          </div>

          {!isSupabaseConfigured && (
            <div className="mb-6 flex items-start gap-3 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4">
              <AlertCircle className="h-5 w-5 flex-shrink-0 text-yellow-400" />
              <div>
                <p className="font-medium text-yellow-400">Supabase Not Configured</p>
                <p className="mt-1 text-sm text-yellow-400/80">
                  Set <code className="rounded bg-yellow-500/20 px-1">NEXT_PUBLIC_SUPABASE_URL</code> and{' '}
                  <code className="rounded bg-yellow-500/20 px-1">NEXT_PUBLIC_SUPABASE_ANON_KEY</code> environment variables to enable the blog CMS.
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="mb-6 rounded-lg bg-red-500/10 p-4 text-red-400">
              {error}
            </div>
          )}

          {isLoading ? (
            <div className="text-center text-zinc-400">Loading posts...</div>
          ) : posts.length === 0 ? (
            <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-8 text-center">
              <p className="mb-4 text-zinc-400">No blog posts yet.</p>
              <Button onClick={handleNew} className="bg-white text-black hover:bg-zinc-200">
                Create Your First Post
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {posts.map((post) => (
                <div
                  key={post.id}
                  className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900 p-4"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-semibold text-white">{post.title}</h3>
                      {post.featured && (
                        <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                      )}
                      {post.published ? (
                        <span className="rounded-full bg-green-500/20 px-2 py-0.5 text-xs text-green-400">
                          Published
                        </span>
                      ) : (
                        <span className="rounded-full bg-zinc-700 px-2 py-0.5 text-xs text-zinc-400">
                          Draft
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-zinc-400">
                      {post.category} • {post.author_name || 'Unknown'} •{' '}
                      {new Date(post.created_at).toLocaleDateString()}
                    </p>
                    {post.excerpt && (
                      <p className="mt-2 line-clamp-1 text-sm text-zinc-500">{post.excerpt}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleTogglePublished(post)}
                      className="text-zinc-400 hover:text-white"
                      title={post.published ? 'Unpublish' : 'Publish'}
                    >
                      {post.published ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(post)}
                      className="text-zinc-400 hover:text-white"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    {isAdmin && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(post.id)}
                        className="text-red-400 hover:text-red-300"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  )
}

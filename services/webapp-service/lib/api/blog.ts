import { supabase, isSupabaseConfigured } from '@/lib/supabase'

export interface BlogPost {
  id: string
  title: string
  slug: string
  excerpt: string | null
  content: string
  category: string
  author_id: string | null
  author_name: string | null
  image_url: string | null
  published: boolean
  featured: boolean
  published_at: string | null
  created_at: string
  updated_at: string
}

export interface BlogPostInput {
  title: string
  slug: string
  excerpt?: string
  content: string
  category?: string
  author_name?: string
  image_url?: string
  published?: boolean
  featured?: boolean
}

export const blogService = {
  /**
   * Get all published blog posts
   */
  async getPublishedPosts(): Promise<BlogPost[]> {
    if (!isSupabaseConfigured) {
      return [] // Return empty array when Supabase is not configured
    }

    const { data, error } = await supabase
      .from('blog_posts')
      .select('*')
      .eq('published', true)
      .order('published_at', { ascending: false })

    if (error) {
      console.error('Error fetching blog posts:', error)
      return [] // Return empty array on error instead of throwing
    }

    return data || []
  },

  /**
   * Get featured blog posts
   */
  async getFeaturedPosts(): Promise<BlogPost[]> {
    if (!isSupabaseConfigured) {
      return []
    }

    const { data, error } = await supabase
      .from('blog_posts')
      .select('*')
      .eq('published', true)
      .eq('featured', true)
      .order('published_at', { ascending: false })
      .limit(3)

    if (error) {
      console.error('Error fetching featured posts:', error)
      return []
    }

    return data || []
  },

  /**
   * Get blog posts by category
   */
  async getPostsByCategory(category: string): Promise<BlogPost[]> {
    if (!isSupabaseConfigured) {
      return []
    }

    const { data, error } = await supabase
      .from('blog_posts')
      .select('*')
      .eq('published', true)
      .eq('category', category)
      .order('published_at', { ascending: false })

    if (error) {
      console.error('Error fetching posts by category:', error)
      return []
    }

    return data || []
  },

  /**
   * Get a single blog post by slug
   */
  async getPostBySlug(slug: string): Promise<BlogPost | null> {
    if (!isSupabaseConfigured) {
      return null
    }

    const { data, error } = await supabase
      .from('blog_posts')
      .select('*')
      .eq('slug', slug)
      .eq('published', true)
      .single()

    if (error) {
      if (error.code === 'PGRST116') {
        return null // Post not found
      }
      console.error('Error fetching post by slug:', error)
      return null
    }

    return data
  },

  /**
   * Get all blog posts (including unpublished) - for admin
   */
  async getAllPosts(): Promise<BlogPost[]> {
    if (!isSupabaseConfigured) {
      return []
    }

    const { data, error } = await supabase
      .from('blog_posts')
      .select('*')
      .order('created_at', { ascending: false })

    if (error) {
      console.error('Error fetching all posts:', error)
      return []
    }

    return data || []
  },

  /**
   * Create a new blog post
   */
  async createPost(post: BlogPostInput): Promise<BlogPost | null> {
    if (!isSupabaseConfigured) {
      console.warn('Cannot create post: Supabase not configured')
      return null
    }

    const { data, error } = await supabase
      .from('blog_posts')
      .insert({
        ...post,
        published_at: post.published ? new Date().toISOString() : null,
      })
      .select()
      .single()

    if (error) {
      console.error('Error creating post:', error)
      throw new Error('Failed to create blog post')
    }

    return data
  },

  /**
   * Update an existing blog post
   */
  async updatePost(id: string, post: Partial<BlogPostInput>): Promise<BlogPost | null> {
    if (!isSupabaseConfigured) {
      console.warn('Cannot update post: Supabase not configured')
      return null
    }

    const updateData: Partial<BlogPostInput & { published_at: string | null }> = { ...post }

    // Set published_at when publishing for the first time
    if (post.published) {
      const { data: existingPost } = await supabase
        .from('blog_posts')
        .select('published_at')
        .eq('id', id)
        .single()

      if (!existingPost?.published_at) {
        updateData.published_at = new Date().toISOString()
      }
    }

    const { data, error } = await supabase
      .from('blog_posts')
      .update(updateData)
      .eq('id', id)
      .select()
      .single()

    if (error) {
      console.error('Error updating post:', error)
      throw new Error('Failed to update blog post')
    }

    return data
  },

  /**
   * Delete a blog post
   */
  async deletePost(id: string): Promise<boolean> {
    if (!isSupabaseConfigured) {
      console.warn('Cannot delete post: Supabase not configured')
      return false
    }

    const { error } = await supabase
      .from('blog_posts')
      .delete()
      .eq('id', id)

    if (error) {
      console.error('Error deleting post:', error)
      throw new Error('Failed to delete blog post')
    }

    return true
  },

  /**
   * Get unique categories from published posts
   */
  async getCategories(): Promise<string[]> {
    if (!isSupabaseConfigured) {
      return []
    }

    const { data, error } = await supabase
      .from('blog_posts')
      .select('category')
      .eq('published', true)

    if (error) {
      console.error('Error fetching categories:', error)
      return []
    }

    const categories = [...new Set(data?.map((p) => p.category) || [])]
    return categories.filter(Boolean) as string[]
  },

  /**
   * Generate a unique slug from title
   */
  generateSlug(title: string): string {
    return title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '')
  },
}

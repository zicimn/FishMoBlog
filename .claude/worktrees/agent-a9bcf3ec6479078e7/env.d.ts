/// <reference types="vite/client" />

declare module 'markdown-it' {
  interface MarkdownItConstructor {
    (options?: {
      html?: boolean
      xhtmlOut?: boolean
      breaks?: boolean
      langPrefix?: string
      linkify?: boolean
      typographer?: boolean
      quotes?: string
      highlight?: (str: string, lang: string) => string
    }): {
      render: (text: string) => string
      renderInline: (text: string) => string
    }
    new(options?: {
      html?: boolean
      xhtmlOut?: boolean
      breaks?: boolean
      langPrefix?: string
      linkify?: boolean
      typographer?: boolean
      quotes?: string
      highlight?: (str: string, lang: string) => string
    }): {
      render: (text: string) => string
      renderInline: (text: string) => string
    }
  }

  const MarkdownIt: MarkdownItConstructor

  export default MarkdownIt
}
<script setup lang="ts">
import {
  detectCodeLanguage,
  highlightStudyCode,
  isMermaidBlock,
  isSubstantialStudyHtml,
  repairMermaidSource,
  studyBodyToHtml,
} from '~/utils/study'

const props = withDefaults(
  defineProps<{
    content: Record<string, unknown> | null | undefined
    title?: string
    compact?: boolean
  }>(),
  {
    title: '',
    compact: false,
  },
)

type CodeExample = { language: string; code: string; html: string }

type MermaidApi = {
  initialize: (config: Record<string, unknown>) => void
  render: (id: string, text: string) => Promise<{ svg: string }>
}

const studyHtmlEl = ref<HTMLElement | null>(null)
const { t } = useI18n()
let mermaidReady: Promise<MermaidApi> | null = null
let mermaidConfigured = false
let renderToken = 0

const richHtml = computed(() => {
  const content = props.content
  if (!content) {
    return ''
  }
  const body = content.body_html
  if (typeof body === 'string' && body.trim()) {
    return studyBodyToHtml(body)
  }
  for (const key of ['instructions', 'content', 'question', 'body_md', 'prompt_md', 'theory_md'] as const) {
    const value = content[key]
    if (typeof value !== 'string' || !value.trim()) {
      continue
    }
    return studyBodyToHtml(value)
  }
  return ''
})

const showBody = computed(() => {
  if (!richHtml.value) {
    return false
  }
  if (!props.compact) {
    return true
  }
  return isSubstantialStudyHtml(richHtml.value, props.title)
})

const images = computed(() => {
  const raw = props.content?.images
  if (!Array.isArray(raw)) {
    return [] as string[]
  }
  return raw.filter(
    (item): item is string => typeof item === 'string' && /^https?:\/\//.test(item),
  )
})

const codeExamples = computed(() => {
  const raw = props.content?.code_examples
  if (!Array.isArray(raw)) {
    return [] as CodeExample[]
  }
  const examples: CodeExample[] = []
  for (const item of raw) {
    if (!item || typeof item !== 'object') {
      continue
    }
    const row = item as Record<string, unknown>
    const code = row.code
    if (typeof code !== 'string' || !code.trim()) {
      continue
    }
    if (showBody.value && richHtml.value.includes(code.trim())) {
      continue
    }
    const language = typeof row.language === 'string' ? row.language : ''
    const detected = detectCodeLanguage(code, language)
    examples.push({
      language: detected,
      code,
      html: highlightStudyCode(code, detected),
    })
  }
  return examples
})

const visibleImages = computed(() => {
  if (!images.value.length || !showBody.value) {
    return props.compact ? [] : images.value
  }
  return images.value.filter((src) => !richHtml.value.includes(src))
})

function decodePreText(inner: string): string {
  return inner
    .replace(/<[^>]+>/g, '')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
}

const enhancedHtml = computed(() => {
  if (!richHtml.value) {
    return ''
  }
  return richHtml.value.replace(
    /<pre(?:\s[^>]*)?>(?:\s*<code(?:\s+class="([^"]*)")?[^>]*>)?([\s\S]*?)(?:<\/code>)?<\/pre>/gi,
    (_match, className: string | undefined, inner: string) => {
      const text = decodePreText(inner)
      const hinted = typeof className === 'string'
        ? (className.match(/language-([\w+-]+)/i)?.[1] ?? className)
        : ''
      if (isMermaidBlock(text, hinted)) {
        const repaired = repairMermaidSource(text)
        const escaped = repaired
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
        return `<pre class="study-mermaid-source"><code class="language-mermaid">${escaped}</code></pre>`
      }
      const lang = detectCodeLanguage(text, hinted)
      const highlighted = highlightStudyCode(text, lang)
      return `<div class="study-code"><div class="study-code-bar"><span>${lang}</span></div><pre><code class="language-${lang}">${highlighted}</code></pre></div>`
    },
  )
})

function loadMermaid(): Promise<MermaidApi> {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('mermaid requires browser'))
  }
  if (mermaidReady) {
    return mermaidReady
  }

  mermaidReady = import('mermaid')
    .then((mod) => {
      const api = (mod.default ?? mod) as MermaidApi
      if (!api?.initialize || !api?.render) {
        throw new Error('mermaid module missing initialize/render')
      }
      return api
    })
    .catch((error) => {
      mermaidReady = null
      throw error
    })
  return mermaidReady
}

async function hydrateMermaid(root: HTMLElement) {
  const sources = Array.from(root.querySelectorAll('pre.study-mermaid-source code.language-mermaid'))
  if (!sources.length) {
    return
  }
  const token = ++renderToken
  let mermaid: MermaidApi
  try {
    mermaid = await loadMermaid()
  } catch (error) {
    console.warn('[study] mermaid load failed', error)
    return
  }
  if (token !== renderToken) {
    return
  }
  if (!mermaidConfigured) {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: 'dark',
      fontFamily: 'inherit',
    })
    mermaidConfigured = true
  }
  for (let index = 0; index < sources.length; index += 1) {
    if (token !== renderToken) {
      return
    }
    const code = sources[index]
    const pre = code.parentElement
    if (!pre || !root.contains(pre)) {
      continue
    }
    const graph = repairMermaidSource(code.textContent || '')
    if (!graph) {
      continue
    }
    const id = `study-mmd-${token}-${index}`
    try {
      const { svg } = await mermaid.render(id, graph)
      if (token !== renderToken || !root.contains(pre)) {
        removeMermaidArtifacts(id)
        return
      }
      const wrap = document.createElement('div')
      wrap.className = 'study-mermaid'
      wrap.setAttribute('role', 'img')
      wrap.setAttribute('tabindex', '0')
      const viewport = document.createElement('div')
      viewport.className = 'study-mermaid-viewport'
      const canvas = document.createElement('div')
      canvas.className = 'study-mermaid-canvas'
      canvas.innerHTML = svg
      viewport.appendChild(canvas)
      wrap.appendChild(viewport)
      const hint = document.createElement('p')
      hint.className = 'study-mermaid-hint'
      hint.textContent = mermaidZoomHint()
      wrap.appendChild(hint)
      scrubMermaidSvg(canvas)
      bindMermaidZoom(wrap, canvas)
      pre.replaceWith(wrap)
      removeMermaidArtifacts(id)
    } catch (error) {
      removeMermaidArtifacts(id)
      console.warn('[study] mermaid render failed', error, graph.slice(0, 120))
      pre.classList.add('study-mermaid-failed')
      pre.setAttribute('title', 'Не удалось отрисовать диаграмму')
    }
  }
}

function mermaidZoomHint(): string {
  return String(t('session.mermaidZoomHint'))
}

function scrubMermaidSvg(wrap: HTMLElement) {
  const svg = wrap.querySelector('svg')
  if (!svg) {
    return
  }
  svg.removeAttribute('height')
  svg.removeAttribute('width')
  svg.style.width = '100%'
  svg.style.height = 'auto'
  svg.style.maxHeight = 'none'
}

function bindMermaidZoom(wrap: HTMLElement, canvas: HTMLElement) {
  let scale = 1
  const min = 0.55
  const max = 2.75

  const apply = () => {
    canvas.style.transform = `scale(${scale})`
  }

  wrap.addEventListener(
    'wheel',
    (event) => {
      if (event.ctrlKey || event.metaKey) {
        return
      }
      event.preventDefault()
      const factor = event.deltaY > 0 ? 0.9 : 1.1
      scale = Math.min(max, Math.max(min, scale * factor))
      apply()
    },
    { passive: false },
  )

  wrap.addEventListener('dblclick', () => {
    scale = 1
    apply()
  })
}

function removeMermaidArtifacts(renderId: string) {
  const selectors = [
    `#${CSS.escape(renderId)}`,
    `#d${CSS.escape(renderId)}`,
    `#${CSS.escape(renderId)}-svg`,
    `body > svg[id^="study-mmd-"]`,
    `body > div[id^="dstudy-mmd-"]`,
  ]
  for (const selector of selectors) {
    document.querySelectorAll(selector).forEach((node) => {
      if (node.closest('.study-mermaid')) {
        return
      }
      node.remove()
    })
  }
}

async function scheduleMermaidHydration() {
  await nextTick()
  const el = studyHtmlEl.value
  if (!el || !showBody.value) {
    return
  }
  await hydrateMermaid(el)
}

watch(
  [enhancedHtml, showBody],
  () => {
    void scheduleMermaidHydration()
  },
  { flush: 'post', immediate: true },
)

onMounted(() => {
  void scheduleMermaidHydration()
})

onBeforeUnmount(() => {
  renderToken += 1
  removeMermaidArtifacts(`study-mmd-${renderToken}`)
  document.querySelectorAll('body > svg[id^="study-mmd-"], body > div[id^="dstudy-mmd-"]').forEach((node) => {
    node.remove()
  })
})
</script>

<template>
  <div
    v-if="showBody || visibleImages.length || codeExamples.length"
    class="study-body"
    :class="{ 'study-body-compact': compact }"
  >

    <div
      v-if="showBody"
      ref="studyHtmlEl"
      class="study-html"
      v-html="enhancedHtml"
    />

    <div v-if="visibleImages.length" class="study-images">
      <figure v-for="(src, index) in visibleImages" :key="`${src}-${index}`" class="study-figure">
        <img :src="src" :alt="`Figure ${index + 1}`" loading="lazy" class="study-image">
      </figure>
    </div>

    <div v-if="codeExamples.length" class="study-examples">
      <div v-for="(example, index) in codeExamples" :key="index" class="study-code">
        <div class="study-code-bar">
          <span>{{ example.language || 'code' }}</span>
        </div>
        <pre><code :class="`language-${example.language}`" v-html="example.html" /></pre>
      </div>
    </div>

  </div>
</template>

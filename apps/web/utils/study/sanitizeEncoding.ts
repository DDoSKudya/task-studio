
export function repairMojibake(text: string): string {
  if (!text || /[А-Яа-яЁё]/.test(text) || !/[À-ÿÐÑ]/.test(text)) {
    return text
  }
  try {
    const bytes = new Uint8Array(text.length)
    for (let i = 0; i < text.length; i += 1) {
      const code = text.charCodeAt(i)
      if (code > 255) {
        return text
      }
      bytes[i] = code
    }
    const decoded = new TextDecoder('utf-8').decode(bytes)
    return /[А-Яа-яЁё]/.test(decoded) ? decoded : text
  } catch {
    return text
  }
}

export function decodeLiteralEntities(html: string): string {

  if (!/&(amp|lt|gt|quot|#\d+|#x[0-9a-f]+);/i.test(html)) {
    return html
  }

  if (!/&lt;\/?[a-z]/i.test(html)) {
    return html
      .replace(/&nbsp;/gi, ' ')
      .replace(/&amp;/g, '&')
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
  }
  return html
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
}

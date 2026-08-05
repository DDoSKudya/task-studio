from __future__ import annotations

# Ниже — «нет статьи» (согласовано с FE LIBRARY_MIN_CONTENT_LEN=40, чуть строже).
MIN_ARTICLE_CHARS = 80

# Прямой HTML достаточно длинный — reader не нужен (экономия RTT).
SKIP_READER_CHARS = 1_500

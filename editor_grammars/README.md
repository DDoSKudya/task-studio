# Грамматики редактора

Пользовательские Monarch-грамматики для языков, у которых в Monaco нет встроенной поддержки.

## Структура

```
editor_grammars/
  example.json
  <language>.json
```

Каждый файл:

```json
{
  "language": "example",
  "monarch": { "tokenizer": { "root": [] } }
}
```

`editor-core` загружает `editor_grammars/<language>.json` во время работы и регистрирует провайдер Monarch.

## Когда добавлять грамматику

- В пакете используется рантайм без встроенного language id Monaco.
- LSP для языка нет или он опционален.
- Подсветка синтаксиса всё равно нужна (`editor_mode: syntax_only` или без контейнера LSP).

## Шаблон

Скопируйте `example.json` и замените `language` и правила tokenizer.

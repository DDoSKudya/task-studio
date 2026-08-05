# runtime_modules — STUB

Манифесты языков и docker-lab лежат здесь, но **сервисы сейчас не читают эту папку как источник правды** для execute/LSP (хардкод / Piston / data).

Не удалять и не «подключать вслепую». Решение: shadow → сравнение с хардкодом → переключение (remediation P543, W8). Или оставить stub до явного ACCEPTED.

Интеграции импорта — только `integration_modules/{stepik,exercism,freecodecamp}` (D12 SUPERSEDED).

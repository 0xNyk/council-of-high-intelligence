# Council of High Intelligence

Русская инструкция по установке и использованию `/council`.

`Council of High Intelligence` - это не веб-приложение и не сервер. Это skill-набор для AI-клиентов Codex, Claude Code и Gemini CLI. Он добавляет команду `/council`, которая собирает несколько AI-персон с разными аналитическими ролями и заставляет их пройти структурированное обсуждение: постановка проблемы, независимый анализ, критика, финальные позиции и итоговый verdict.

## Что делает совет

- выбирает подходящую группу агентов под задачу;
- заставляет каждого участника сначала переформулировать проблему;
- проводит независимый анализ без преждевременного влияния других участников;
- анонимизирует второй раунд, чтобы снизить конформизм;
- требует финальную `STANCE`-строку для подсчета позиции;
- выбирает отдельного `Chairman`, который не участвовал в обсуждении и синтезирует итог;
- показывает компромиссы, kill criteria и конкретный следующий шаг.

## Быстрая установка для Codex

```bash
git clone https://github.com/0xNyk/council-of-high-intelligence.git
cd council-of-high-intelligence
./install.sh --codex-only --copy-configs
```

После установки перезапустите Codex.

Проверить установку без записи файлов:

```bash
./install.sh --dry-run --codex-only
```

Проверить структуру проекта:

```bash
./scripts/council-simulation-checklist.sh
```

Проверить доступные AI-провайдеры:

```bash
./scripts/detect-providers.sh
```

## Установка для Claude Code

```bash
git clone https://github.com/0xNyk/council-of-high-intelligence.git
cd council-of-high-intelligence
./install.sh
```

## Установка для Codex и Claude Code сразу

```bash
./install.sh --codex --copy-configs
```

## Установка для Gemini CLI

```bash
./install.sh --gemini --copy-configs
```

## Важное про команды

Сами команды и флаги остаются на английском, потому что это интерфейс CLI:

```text
/council
--quick
--duo
--triad
--profile
--members
--dry-route
--explain-route
```

Но вопрос можно писать по-русски:

```text
/council Почему государства постоянно воюют?
```

## Основные режимы

Полный режим:

```text
/council Стоит ли нам открывать исходный код нашего агентного фреймворка?
```

Быстрый режим:

```text
/council --quick Стоит ли добавить кэширование в этот модуль?
```

Режим спора двух противоположных позиций:

```text
/council --duo Стоит ли переписывать монолит на микросервисы?
```

Режим конкретной триады:

```text
/council --triad decision Стоит ли купить конкурента или разработать функцию самостоятельно?
```

Явный выбор участников:

```text
/council --members socrates,feynman,ada Насколько надежна наша архитектура?
```

## Новый режим объяснения маршрута

`--explain-route` показывает, почему совет выбрал именно такую панель, какие альтернативы отклонил, кто получил доменный вес 1.5x, какой Chairman будет синтезировать итог и какие провайдеры/модели будут использованы.

```text
/council --explain-route --triad conflict Почему государства постоянно воюют?
```

Только показать маршрут и не запускать обсуждение:

```text
/council --dry-route --explain-route --profile geopolitics Какие риски у этого международного конфликта?
```

## Профили

`classic` - все 18 участников.

```text
/council --profile classic Нужно ли нам менять стратегию продукта?
```

`exploration-orthogonal` - поиск неизвестных неизвестных и сильных альтернативных рамок.

```text
/council --profile exploration-orthogonal Какой риск мы не видим в этой идее?
```

`execution-lean` - быстрые решения, запуск, откат, стабильность.

```text
/council --profile execution-lean Стоит ли выпускать релиз сегодня?
```

`geopolitics` - государства, войны, санкции, альянсы, геополитические риски.

```text
/council --profile geopolitics Почему государства постоянно воюют?
```

`startup` - стартап, продукт, рынок, монетизация, execution.

```text
/council --profile startup Как нам выбрать модель монетизации?
```

`security` - угрозы, защита, надежность, атаки, инциденты.

```text
/council --profile security Как оценить угрозы для нашей системы?
```

`research` - техническая неопределенность, эксперименты, модели, формальные ограничения.

```text
/council --profile research Как проверить эту ML-гипотезу?
```

`policy` - регулирование, институты, этика, общественный интерес.

```text
/council --profile policy Как оценить последствия нового правила?
```

## Триады

```text
/council --triad architecture Как спроектировать новый backend?
/council --triad strategy Какой у нас конкурентный ров?
/council --triad conflict Как выйти из конфликта с партнером?
/council --triad risk Какие риски у запуска в продакшн?
/council --triad product Как улучшить онбординг?
/council --triad ai Стоит ли fine-tune open-source LLM?
/council --triad design Как упростить UX?
```

## Маршрутизация моделей

По умолчанию совет пытается найти доступных провайдеров:

- Anthropic через host/sub-agent;
- OpenAI через `codex`;
- Google через `gemini`;
- Ollama через локальные модели;
- Cursor CLI через `cursor-agent`;
- NVIDIA NIM через `NVIDIA_API_KEY`.

Отключить auto-routing:

```text
/council --no-auto-route --quick Стоит ли добавить Redis?
```

Использовать ручную карту моделей:

```text
/council --models configs/provider-model-slots.example.yaml --profile exploration-orthogonal Какой главный риск у стратегии?
```

Переопределить Chairman:

```text
/council --chairman openai --triad decision Стоит ли нам принять это предложение?
```

## Единый протокол

Канонический список флагов, триад, профилей, провайдеров и обязательных verdict-секций лежит в:

```text
protocol.json
```

Проверить, что skill-файлы и конфиги не разъехались с протоколом:

```bash
python3 scripts/validate-protocol.py
```

Эта проверка также запускается из:

```bash
./scripts/council-simulation-checklist.sh
```


---
type: Index
title: 001 — «Бургер» MVP (bundle)
description: Точка входа в OKF-бандл feature 001. Что строим, где источники истины, с чего начинать.
tags: [spec-kit, "001", index]
timestamp: 2026-08-19T00:00:00Z
feature: 001-burger-mvp
status: draft
---

# 001 — «Бургер» MVP

OKF-бандл feature 001, оформленный по Spec Kit. Путь файла = идентичность концепта;
фронтматтер каждого — YAML, тело — markdown; связи между концептами обычными ссылками.

## Концепты бандла

- [spec.md](spec.md) — `Feature Spec`: что строим, границы 001, критерий приёмки,
  зафиксированные решения B1–B4.
- [readiness-gate.md](readiness-gate.md) — `Readiness Gate`: что блокирует час 0,
  что закрываем на ходу, что не чиним. **Читать до раздачи планов.**
- [log.md](log.md) — `Log`: хронология решений по 001.
- Потоки (specify + plan, стоп до tasks/кода):
  [B spec](stream-b-phase1.md) / [plan](stream-b-plan.md),
  [C spec](stream-c-phase2.md) / [plan](stream-c-plan.md),
  [D spec](stream-d-frontend.md) / [plan](stream-d-plan.md).

## Внешние источники истины (корень репозитория)

Не переписаны в бандл сознательно — это добытое живыми замерами знание, дублирование
плодит рассинхрон. Кросс-ссылки ведут туда напрямую.

- [mvp-spec.md](../../mvp-spec.md) — контракт API, схема, кластеризация, продуктовые решения.
- [open-issues.md](../../open-issues.md) — блокеры B1–B4, посчитанные бюджеты.
- [data-collection-spec.md](../../data-collection-spec.md) — методика ингеста, ловушки.
- [tutu-mcp-field-test.md](../../tutu-mcp-field-test.md) — живые замеры Tutu/OSM/Wikidata.
- [ingredients.yaml](../../ingredients.yaml) — словарь ингредиентов с плотностью.

## Оркестрация и планы исполнителей

- [plans/00-orchestration.md](../../plans/00-orchestration.md) — потоки, граф зависимостей, таймлайн.
- [plans/deploy-vps.md](../../plans/deploy-vps.md) — выкладка (nginx 8080, G6).
- [plans/architect.md](../../plans/architect.md), [plans/worker-A-ingest.md](../../plans/worker-A-ingest.md),
  [plans/worker-B-phase1.md](../../plans/worker-B-phase1.md),
  [plans/worker-C-phase2.md](../../plans/worker-C-phase2.md),
  [plans/worker-D-frontend.md](../../plans/worker-D-frontend.md).

## С чего начинать

1. [spec.md](spec.md) — рамка и границы.
2. [readiness-gate.md](readiness-gate.md) §A — 10 блокеров, прогнать до кода.
3. [plans/00-orchestration.md](../../plans/00-orchestration.md) — раздать потоки.

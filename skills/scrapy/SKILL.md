---
name: scrapy
description: Build bounded web crawlers with Scrapy. Use for spiders, selectors, pagination, item pipelines, throttling, feed exports, and resumable crawls.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/scrapy
  created: "2026-09-10"
  updated: "2026-09-10"
---

# Scrapy

Use Scrapy for scheduled crawling and structured extraction; [playwright](../playwright/SKILL.md) owns browser interaction when rendering is actually required.

## Workflow

1. Define allowed hosts, paths, data fields, page/time budgets, and output retention. Add `scrapy` with `uv add scrapy`; start a new crawler with `uv run scrapy startproject <name>` in a fresh directory.
1. Test CSS/XPath selectors against saved HTML using `scrapy.http.HtmlResponse`. Cover missing fields, duplicate links, and pagination termination before making network requests.
1. Implement a named spider, `allowed_domains`, and explicit start URLs. Use `response.follow` for relative links and a pipeline for validation and storage; inspect the locked version before using async `start()`.
1. Set `ROBOTSTXT_OBEY`, an identifying user agent, download timeout, per-domain concurrency, delay or AutoThrottle, and close-spider time/page limits. Disable the telnet console when unused.
1. Run a bounded local fixture crawl, then the authorized target. Adapt `uv run scrapy crawl <spider> -O <fresh-output.jsonl>`; inspect item counts, duplicate filtering, HTTP failures, and close reason.
1. Use a unique `JOBDIR` per resumable crawl and verify resume without duplicate persisted records; do not share state directories across jobs.

## Gotchas

- `-O` overwrites a feed; use a fresh destination. `-o` appends and may produce invalid concatenated JSON documents if used carelessly.
- `allowed_domains` is a crawl control, not a network security boundary; validate externally supplied start URLs and redirects when input is untrusted.
- Respect access controls and stop on blocks; retries and proxy rotation are not a remedy for missing authorization.

## Official Skills

No consumer Agent Skill was found in the inspected [scrapy/scrapy](https://github.com/scrapy/scrapy) repository on 2026-09-10. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [Tutorial](https://docs.scrapy.org/en/latest/intro/tutorial.html) · [Settings](https://docs.scrapy.org/en/latest/topics/settings.html) · [Jobs](https://docs.scrapy.org/en/latest/topics/jobs.html)

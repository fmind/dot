# TypeScript Website Architecture

Choose the smallest architecture before scaffolding; a Firebase-backed client-side app is already full stack, and SSR is a rendering choice rather than a prerequisite for backend features.

| Need                                             | Default                               | Add                                                             |
| ------------------------------------------------ | ------------------------------------- | --------------------------------------------------------------- |
| Authenticated or highly interactive UI           | Client-side rendering (CSR)           | [angular](../angular/SKILL.md) and static hosting               |
| Public pages with stable content                 | Static generation (SSG) per route     | Angular server routing and static hosting                       |
| Public pages with request-time data              | Server-side rendering (SSR) per route | Angular server routing and Firebase App Hosting                 |
| Authentication, data, files, or server functions | Firebase                              | [firebase](../firebase/SKILL.md) and local emulators            |
| Generative AI inside the product                 | Genkit behind a server boundary       | [genkit](../genkit/SKILL.md), usually deployed through Firebase |

- **Shape by feature**: colocate each route's components, state, data access, and tests; keep composition roots thin and lazy-load routes instead of creating generic `shared`, `core`, or `utils` layers pre-emptively.
- **Web quality**: semantic HTML, keyboard and focus behavior, accessible loading and error states, bundle budgets, and per-route rendering chosen from measured SEO and performance needs.
- **Test by risk**: units and components in Vitest, dependency hygiene in Knip, a small set of critical journeys in [playwright](../playwright/SKILL.md), Firebase emulator tests and Genkit evaluations only once those layers exist.
- **Deploy separately**: deployment requires explicit authorization and follows [firebase](../firebase/SKILL.md) for Hosting or App Hosting, or [cloud-run](../cloud-run/SKILL.md) for a container.

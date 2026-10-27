# Assessment: grok-workspace.zip

**Reviewed:** 2026-10-27  
**Decision:** Reuse selected decision-process concepts and engineering checks. Do not import the workspace wholesale or treat it as the business platform.

## Executive conclusion

**Yes, selectively.** The archive contains a React/TanStack application called **Helm**, a personal decision and life-systems cockpit. Its decision records, assumption review, pre-mortem, score sensitivity, goal indicators and weekly review loop map closely to the decision discipline we need to operate AI Digital Growth.

It is **not** an acquisition, audit, CRM, campaign, delivery, invoicing or client-outcome system. Its current persistence is browser-local Zustand state using localStorage (key helm-ledger-v1); its environment declares authentication disabled and database deployment disabled. That is acceptable for a single-device prototype, not for shared or durable business records.

## What the archive contains

- Responsive Home/Cockpit, Decide, Signal, Horizon and Review views.
- Decision records with context, weighted criteria, options and scores, pre-mortem, causes, kill criterion, second-order effects, selected option, override rationale and forgone value.
- A deterministic-seeded sensitivity run that perturbs subjective criterion scores using Gaussian noise and reports option win rates, score ranges and ties.
- An assumptions ledger with confidence (1–5), stakes, review date, status, last review and links to decisions or goals.
- Goals and indicators, daily habit/energy logging, and a weekly review structured around priority, stop and test.
- Developer checks for migrations, browser smoke comparisons, environment invariants, atomic file operations and regression tests.
- Platform-specific Grok App Builder instructions, preview authentication plumbing, PWA injection, generated Vercel output and static preview artifacts.

## Reuse decision

### Adopt as process patterns

1. **Decision packet:** facts and constraints; explicit alternatives; weighted criteria; evidence and confidence for each material score; pre-mortem; kill/reversal criterion; second-order effects; forgone opportunity cost; selected option; override rationale.
2. **Assumption ledger:** statement; type (commercial, technical, legal, behavioral); confidence; stakes; evidence; review date; status; linked decisions/experiments; observations that would strengthen or break it.
3. **Sensitivity analysis:** use only to expose fragile rankings under subjective score noise. It is not a probability that an option will succeed or proof that criteria/weights are correct. Correlated criteria, biased scores and poorly chosen alternatives remain outside the simple model.
4. **Weekly operating review:** what matters next, what to stop, which assumption to test, what data actually showed, and which decision needs revisiting.
5. **Quality gates:** explicit test evidence, before/after browser baselines, bounded processes and fail-closed verdicts for our application's CI and QA where appropriate.

### Do not adopt as-is

- Do not treat Helm's seeded life-system data as business evidence.
- Do not use browser localStorage as the source of truth for leads, suppression, approvals, client projects, costs or outcome records.
- Do not infer production-ready authentication/database behavior: .grok/app-env.json has auth off and database deployment disabled.
- Do not assume the export is a reproducible production build. It contains prebuilt Vercel output, but dependencies are absent from the archive and no fresh production build/browser run was completed.
- Do not copy .grok platform skills, preview authentication plumbing, generated bundles or platform-specific server/PWA integration into AI Digital Growth without compatibility, ownership and security review.
- Do not adopt sensitivity output as a calibrated probability. It answers a narrow question: how rankings move when score inputs are perturbed by a chosen noise parameter.

## Verification performed

- ZIP listing and extraction completed; 364 entries observed.
- Confirmed the core app modules and views described above.
- Confirmed src/lib/helm/store.ts persists the ledger to browser localStorage, not to an application database.
- Confirmed .grok/app-env.json declares authentication disabled and database deployment disabled.
- A platform-specific preview authentication module contains a fixed client credential. Do not copy that module into our repository; the platform owner should review the exposure boundary if the archive has been shared beyond its intended environment.
- No obvious provider API key pattern was found by a basic source scan; that is not a substitute for a full secret scanner.

### Tests

- Running the included npm test under Node 22 **failed**: 191 tests passed and 6 failed in the script test phase.
- All six failures are in scripts/grok-pwa-plugin.test.mjs, involving Open Graph/app-title behavior. The injector emitted the fixed title “Helm” where tests expected dynamic page/app titles or a published slug fallback. This is a source/test inconsistency to resolve before claiming a green suite; it does not establish a defect in the business features we might borrow.
- Since the script test phase failed, the chained TypeScript test phase did not run through npm test.
- Running the TypeScript test command separately without installing dependencies yielded 10 passing tests and 2 test-file failures caused by missing runtime packages (@tanstack/react-start and jose). These are environment/dependency blockers, not verified assertion failures.
- No dependency install, typecheck, lint, production build, browser smoke test or deployed runtime test was performed.

## Fit for AI Digital Growth

| Capability | Fit | Decision |
|---|---|---|
| Alternative/trade-off discipline | High | Adopt in decision records |
| Pre-mortem, kill criteria and second-order effects | High | Adopt in important decisions/experiments |
| Assumption confidence and review cadence | High | Adopt; add evidence and owner |
| Sensitivity analysis for market/offer selection | Medium | Optional heuristic after criteria are evidence-based |
| Weekly executive review | High | Use a lightweight operating loop |
| Lead discovery / website audit / CRM / campaigns | Low | Not provided by the archive |
| Shared system of record / audit trail | Low | Needs server-side durable storage if/when implemented |
| Current product/runtime for direct reuse | Low–medium | Keep as reference; re-evaluate only if an internal founder cockpit becomes a demonstrated need |

## Integration path

Do not create a separate dashboard merely because the workspace looks polished. The current AI-Digital-Growth repository already has a decision log, market adapters, implementation backlog and verification plan. Adopt the decision and assumption templates and use them while running the first commercial experiment. Only build an interactive internal cockpit if managing these records manually becomes a demonstrated bottleneck.

## Confidence and remaining uncertainty

- **High confidence:** app structure, local storage choice, environment flags and test outcomes are directly observable in the archive.
- **Medium confidence:** reusability of UI and domain logic; a fresh dependency install, typecheck and browser run are needed to assess portability.
- **Unverified:** ownership/license obligations for embedded platform-specific files, deployed behavior, external integration capability, and whether the app was intended as a product or prototype.

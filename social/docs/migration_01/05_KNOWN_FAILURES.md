# Known failures and traps

## 1. UI-first development

Multiple Social UI versions were built/rejected while the actual product still had zero real Reel packages and zero finished reels.

Rule: do not spend the migration on UI polish.

## 2. Backend-is-the-product thinking

Database contracts, queues, render jobs and provider safety infrastructure are useful only when they support the actual Reel.

Rule: infrastructure milestones are not product completion.

## 3. Missing OpenAI key dead-end

The prior runtime stopped at a missing key even though the needed deliverable was mostly text/package construction.

Rule: Claude itself can author grounded package content. Do not reproduce the blocker.

## 4. Fake/demo packages

Placeholders and simulated success are explicitly rejected.

Rule: only materialized files with grounded claims count.

## 5. Social/MediaEngine boundary confusion

Do not rewrite MediaEngine while solving Social. Social produces a package; MediaEngine renders.

## 6. Old V7 branch

V7 and older UI prototypes are historical references only. They are not the migration baseline.

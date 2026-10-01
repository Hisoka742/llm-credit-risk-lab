---
version: 1
slug: "site-src-app-tsx"
primary_target: "site/src/App.tsx"
related_targets: []
---

# Surface brief: showcase site (site/)

Scope: single-page showcase of the LLM Credit Risk Lab study. Visitor mode: Persuade.

Audience and job: a bank risk-modeling / LLM hiring team deciding in a few minutes whether the author measures correctly. Action: read the results, then open the repository or make contact. Proof: real numbers from reports/runs/*/metrics.json, real borrower descriptions, real LLM pilot outputs, stated limitations. Constraints: no invented numbers, names, links or testimonials; E2/E3 shown as in progress; brief pins dark cinematic, display + clean sans, Three.js hero, smooth scroll, scroll reveals, magnetic CTA, scroll-highlighted hook text, glass bento, ticker, full-screen footer.

Unresolved: author name, GitHub URL, contact email, deploy target.

## Direction contract

THESIS: The words are the data. The page is built from borrowers' real sentences and the model's reading is drawn onto them. It refuses the category default of an abstract glowing orb over a neon-accent dashboard.

OWN-WORLD: Near-black listing-night ground (#0B0E13), warm paper text (#F1ECE2), and one diverging data pair used only for meaning: warm (#FF5A3C) for words and outcomes that raise risk, cool (#5FD4B1) for those that lower it. Oversized borrower sentences are the imagery. Frosted listing cards over a drifting field of loan motes. Clash Display for voices and headings, Satoshi for reading, JetBrains Mono only for real JSON and numbers.

STORY: The visitor reads a borrower, sees the measured answer immediately, learns how leakage, time split and bootstrap were handled, sees the honest result (small, not significant), reads the limits, and opens the study.

FIRST VIEWPORT: One real borrower sentence at display scale, left-aligned, words tinted by the text model's coefficients, over a field of 125,700 motes (defaults warm). Below it, one line of measured answer (+0.004 Gini, p = 0.079) and the primary action "Read the study" with a secondary "See the method".

FORM: In Their Own Words, position 5 on the re-rolled grounded list; seed key 9086e820. Signature interaction: word-level heat that resolves as the sentence enters view, and a scroll-tied paragraph whose words light as the reader advances. Motion grammar: one orchestrated entrance per section, strong ease-out, transform/opacity/blur only, reduced-motion falls back to static.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

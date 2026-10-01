---
name: LLM Credit Risk Lab
description: A dark, text-first showcase where borrowers' own sentences are the imagery and colour only ever means risk.
colors:
  ink: "#0b0e13"
  ink-2: "#131822"
  paper: "#f1ece2"
  muted: "#a8a399"
  faint: "#8f8b84"
  line: "rgb(241 236 226 / 0.12)"
  warm: "#ff5a3c"
  cool: "#5fd4b1"
typography:
  display:
    fontFamily: "Clash Display, Satoshi, system-ui, sans-serif"
    fontSize: "clamp(2.6rem, 7.2vw, 6rem)"
    fontWeight: 500
    lineHeight: 1.02
    letterSpacing: "-0.03em"
  statement:
    fontFamily: "Clash Display, Satoshi, system-ui, sans-serif"
    fontSize: "clamp(1.9rem, 4.4vw, 4rem)"
    fontWeight: 500
    lineHeight: 1.12
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Clash Display, Satoshi, system-ui, sans-serif"
    fontSize: "clamp(2rem, 4.2vw, 3.5rem)"
    fontWeight: 500
    lineHeight: 1.05
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Clash Display, Satoshi, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 500
    lineHeight: 1.25
    letterSpacing: "-0.015em"
  subtitle:
    fontFamily: "Clash Display, Satoshi, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 500
    lineHeight: 1.4
  body-lead:
    fontFamily: "Satoshi, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.625
  body:
    fontFamily: "Satoshi, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.625
  label:
    fontFamily: "Satoshi, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.43
  caption:
    fontFamily: "Satoshi, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 400
    fontFeature: "tnum, lnum"
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, SFMono-Regular, monospace"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.7
rounded:
  card: "20px"
  control: "999px"
  input: "12px"
  focus: "6px"
spacing:
  gutter: "1.25rem"
  gutter-md: "2.5rem"
  container: "1400px"
  section: "6rem"
  section-md: "9rem"
  card: "1.5rem"
  card-md: "2rem"
  grid-gap: "1.25rem"
components:
  button-primary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    height: "3.25rem"
    padding: "0 1.6rem"
  button-primary-hover:
    backgroundColor: "#ffffff"
  button-ghost:
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    height: "3.25rem"
    padding: "0 1.6rem"
  button-ghost-hover:
    backgroundColor: "rgb(241 236 226 / 0.06)"
  button-icon:
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    size: "3rem"
  card-glass:
    textColor: "{colors.paper}"
    rounded: "{rounded.card}"
    padding: "{spacing.card}"
  input:
    backgroundColor: "rgb(241 236 226 / 0.04)"
    textColor: "{colors.paper}"
    rounded: "{rounded.input}"
    padding: "0.75rem 1rem"
  nav:
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    height: "4rem"
  code-block:
    textColor: "{colors.paper}"
    typography: "{typography.mono}"
    rounded: "{rounded.card}"
    padding: "1.25rem"
---

# Design System: LLM Credit Risk Lab

## Overview

**Creative North Star: "In Their Own Words"**

The page is built from borrowers' real sentences. Text is the imagery: one borrower sentence set at display scale opens the page, and the model's reading is drawn directly onto the words as colour. Behind everything sits a fixed field of small motes on a near-black ground, and the field is data too: one mote per loan in the study, positions seeded so it is identical on every load, with the warm share equal to the measured default rate. The hero carries a written key for both the word colours and the field, so nothing coloured or moving is left unexplained.

The system is quiet so that the one coloured thing on screen can be trusted. Ground, text, borders, charts and buttons are all drawn from two values, near-black ink and warm paper, with paper at reduced alpha doing the work of greys. Density is editorial rather than dashboard: large left-aligned headings, short measures, generous vertical rhythm, and frosted cards only where content is genuinely a contained unit.

Motion follows one grammar. Anything entering uses a single strong ease-out curve (cubic-bezier(0.23, 1, 0.32, 1)) over 0.5 to 1 second, moving by transform, opacity and a short blur only, once per element as it enters view. Two scroll-tied devices carry the story: word-level heat that settles onto the hero sentence after the words arrive, and a paragraph whose words light from 16% to full opacity as the reader advances. Every animated component reads one switch (`useCalm`); when the visitor's system asks for reduced motion, content renders settled, smooth scrolling is not started, and the field draws a single static frame.

**Key Characteristics:**
- Borrower sentences at display scale are the imagery; there are no illustrations or photographs.
- Two values (ink and paper) draw the whole interface; colour appears only as meaning.
- A fixed, seeded WebGL field that is a data plot, explained by a key in the hero.
- Frosted glass cards over the field, flat sections veiled in translucent ink.
- One ease-out curve for every entrance, with a complete static fallback.
- Numbers always present as text in tabular figures, never only in a chart or in 3D.

## Colors

A two-value ground and text pair, plus one diverging data pair that is spent only on meaning.

### Primary
- **Warm Paper** (`paper`): all primary text, the primary button fill, focus rings, text selection, the caret, and every monochrome data mark (interval lines, dots, bars, curves). It is the interface accent; there is no separate brand hue. Used at reduced alpha for everything in between: 90% and 85% for softened body copy, 60/45/30% for chart tone steps, 28% for ghost button borders, 25% for input borders, 10% for card borders, 4 to 7% for card and input fills.

### Secondary
- **Default Warm** (`warm`): words the text model associates with default, the "Charged off" outcome on a listing, the defaulted motes in the field, and the bars and heading of the "linked to default" term list.
- **Repayment Cool** (`cool`): words associated with repayment, and the bars and heading of the "linked to repayment" term list.

Word tinting is a blend, not a flat fill: paper is mixed toward warm or cool by 40% to 100% according to the word's model weight, and words with a weight under 0.1 stay plain paper.

### Neutral
- **Listing-Night Ink** (`ink`): the page ground, text on the primary button, the ring that separates a data dot from its line. Laid over the field at 55 to 70% as a veil on alternating sections, 80% under the scrolled navigation, 95% under the open phone menu.
- **Raised Ink** (`ink-2`): the opaque card fill used when the visitor asks for reduced transparency.
- **Muted Paper** (`muted`): secondary prose, captions, navigation links at rest, helper text. 7.7:1 on ink.
- **Faint Paper** (`faint`): the quietest tier, for JSON keys, axis year labels and the dashed "pending" mark. 5.7:1 on ink.
- **Hairline** (`line`): section rules, table row dividers, chart gridlines, the divider inside a card.

### Named Rules
**The Meaning-Only Rule.** Warm and cool are a diverging data pair: warm raises predicted default, cool lowers it. They are never used as interface decoration, so a coloured word, bar or dot always says something about risk. Every use is accompanied by a text label or key; colour is never the only carrier.

**The Paper Accent Rule.** The interface accent is the paper colour itself. Primary actions are paper on ink, focus is a 2px paper outline, selection inverts to paper. No third hue exists for buttons, links or highlights.

**The Paper Chart Rule.** Charts that do not encode risk direction are drawn in paper alone, with series separated by opacity (100%, 60%, 45%, 30%) rather than by hue.

## Typography

**Display Font:** Clash Display, weight 500 (with Satoshi, system-ui fallback)
**Body Font:** Satoshi, weights 400, 500, 700 (with system-ui, -apple-system, Segoe UI fallback)
**Label/Mono Font:** JetBrains Mono, weights 400, 500 (with ui-monospace, SFMono-Regular fallback)

**Character:** A wide, assertive display face carries voices and headings at a single weight, so emphasis comes from scale rather than boldness. A calm humanist sans does the reading. The pairing reads as editorial rather than technical; the mono face is held back so that when it appears, the reader knows they are looking at a real artifact.

### Hierarchy
- **Display** (500, clamp(2.6rem, 7.2vw, 6rem), 1.02, -0.03em): the hero borrower sentence, capped near 17 to 18ch. The closing footer statement uses the same ceiling with a tighter setting (clamp(3rem, 9vw, 6rem), 0.98, -0.035em).
- **Statement** (500, clamp(1.9rem, 4.4vw, 4rem), 1.12, -0.02em): the scroll-lit question paragraph, 24 to 26ch.
- **Headline** (500, clamp(2rem, 4.2vw, 3.5rem), 1.05, -0.025em): one per section, capped between 14 and 20ch.
- **Title** (500, 1.5rem rising to 1.75rem from 768px, 1.25, -0.015em): card headings and list-item headings.
- **Subtitle** (500, 1.25rem): definition terms, limitation leads, small block headings.
- **Body lead** (400, 1.125rem, 1.625, muted): the paragraph under a headline, 46 to 62ch.
- **Body** (400, 1rem, 1.625): card and list prose (0.975rem inside cards), 44 to 58ch. Listing text is 1.05rem at 1.6 in full paper.
- **Label** (400 or 500, 0.875rem, muted): captions, card metadata, form labels, navigation links, footnotes.
- **Caption** (400, 0.75rem, tabular figures): axis ticks and chart scale labels.
- **Mono** (400, 12.5px to 14px, 1.7 to 1.9): JSON output, column names, shell commands, file paths.

### Named Rules
**The Real Artifact Rule.** JetBrains Mono is only for things that are literally code: JSON the model returned, dataframe column names, commands, file paths. Measured numbers in prose, tables and charts are set in Satoshi with tabular lining figures, not in mono.

**The Open Word Rule.** Every use of the display face carries word-spacing of 0.14em. Clash Display sets tight word spaces, and with negative tracking they close up at heading sizes.

**The One Weight Rule.** Display type is always weight 500. Hierarchy between display, statement, headline and title is made with size alone.

## Layout

A single left-aligned column inside a 1400px container, with gutters of 1.25rem that widen to 2.5rem from 768px. Nothing is centred: headings, prose and actions share the left content edge, and measures are capped in `ch` so headings break into two or three lines and prose stays readable inside the wide container. Sections are separated by vertical space (6rem, 9rem from 768px; the question section takes 7rem and 11rem), not by rules or boxes. The hero and the footer each fill the viewport (100dvh).

Two-column sections use deliberately unequal tracks (1fr/1.1fr, 1fr/1.15fr, 0.8fr/1.2fr) from 1024px and collapse to one column below. The method section is a twelve-column bento from 1024px with spans of 7 (two rows), 5, 5, 5, 4 and 3, two columns from 768px, one below, on a 1.25rem gap. Reviewed listings sit in a horizontal snap rail of cards min(86vw, 30rem) wide; the rail's inline padding is computed so the first card lines up with the page's content edge at any width, and it is driven by scroll, keyboard focus and a pair of circular arrow buttons. Headings sit 3rem above their content; cards pad 1.5rem, 2rem from 768px.

Layering has three levels only: the field at 0, content at 10, navigation at 40.

## Elevation & Depth

Depth is layered, not shadowed. The lowest plane is the fixed mote field, which dims from full to half opacity over the first 700px of scroll. Sections either sit directly on it or lay a translucent ink veil over it. The only raised surface is the frosted card. The navigation is flat and transparent at the top of the page and becomes a frosted bar with a hairline once the page has scrolled 40px.

### Shadow Vocabulary
- **Glass card** (`box-shadow: inset 0 1px 0 rgb(241 236 226 / 0.1), 0 24px 60px -30px rgb(0 0 0 / 0.7)`): a top-edge highlight plus a deep, soft, tightly inset drop. Paired with a 160deg paper gradient fill (7% to 2.5%), a 10% paper border, and `backdrop-filter: blur(18px) saturate(140%)`.

### Named Rules
**The One Raised Surface Rule.** The frosted card is the only shadowed element. Buttons, inputs, navigation and charts are flat and are separated by borders, hairlines or opacity.

**The Opaque Fallback Rule.** Under `prefers-reduced-transparency`, the frosted card drops its blur and becomes solid Raised Ink.

## Shapes

Three radii, assigned by role: cards are softly rounded (20px), every control is a full pill (999px), text inputs sit between them (12px). Focus outlines round to 6px. Data marks follow the control language: interval lines, bars and split strips are pill-ended, points are circles with an ink ring. Borders are always 1px and always paper at low alpha; there are no solid coloured borders and no side stripes.

## Components

### Buttons
- **Shape:** full pill (999px), 3.25rem tall, 1.6rem inline padding, label at weight 500 with an optional 18 to 20px icon after a 0.6rem gap.
- **Primary:** paper fill, ink text. One per view. The primary action is wrapped in a magnetic lean toward the cursor (28% of the pointer offset, spring 220/18, mouse and pen only).
- **Ghost:** transparent with a 1px paper border at 28%, paper text.
- **Icon:** the ghost button made circular (2.75rem in the navigation, 3rem for rail arrows), icon only, always with an accessible label.
- **Hover / Focus:** primary lifts to pure white; ghost border rises to 60% with a 6% paper fill; both only on hover-capable fine pointers. Press scales to 0.97 over 160ms on the ease-out curve. Focus is the global 2px paper outline at 3px offset.

### Cards / Containers
- **Corner Style:** softly rounded (20px).
- **Background:** frosted paper gradient over the field; see Elevation.
- **Shadow Strategy:** the single glass shadow.
- **Border:** 1px paper at 10%.
- **Internal Padding:** 1.5rem, 2rem from 768px. An internal hairline separates a card's content from its footer line.
- **Behaviour:** bento cells tilt up to 3.2 degrees toward a mouse pointer on a spring and enter with a 28px rise, 0.97 scale and 60ms stagger. Rail cards enter from 48px to the right.

### Inputs / Fields
- **Style:** 12px radius, 1px paper border at 25%, paper fill at 4%, 0.75rem by 1rem padding, a weight 500 label above at 0.875rem.
- **Hover / Focus:** border rises to 45% on hover and to full paper on focus, alongside the global focus outline.
- **Help / Error:** a muted helper sentence sits under the field and is replaced by a plain-language error sentence announced as an alert.

### Navigation
- **Style:** fixed 4rem bar inside the container. The product name in the display face at 1.125rem on the left; four section links on the right in 0.875rem muted text that brighten to paper on hover.
- **Scrolled:** after 40px the bar takes an 80% ink fill, a 24px backdrop blur and a hairline below.
- **Mobile:** below 768px the links move behind one circular ghost icon button; the open panel lists them in the display face at 1.5rem on 95% ink.

### Heat Text (signature)
Borrower text with each word tinted by its weight in the text-only model. In running copy the tint is static. In the hero each word rises 0.35em out of an 8px blur on a 55ms stagger, then its colour settles 0.55s later, so the reader sees the sentence first and the model's reading second. The last two words are kept together so no word sits alone on the final line. A key naming both colours always accompanies it.

### Loan Field (signature)
A fixed full-viewport point field behind all content. One mote per loan on wide screens with six or more cores, otherwise a 36,000-mote sample with the same seed and default share. Defaulted loans are warm, larger and near-opaque; repaid loans are paper at 32 to 56% opacity. Motes drift slowly, shift with scroll, and the whole field leans a few degrees toward the pointer. It loads after first paint and is hidden from assistive technology; its meaning is stated in the hero key.

### Interval Row (signature)
A results table row with three tracks: experiment id and label, a plot track, and the value with its interval as text. The plot shows a 3px paper line for the 95% interval and a 14px paper dot with an ink ring for the estimate, over hairline gridlines. An experiment without a result shows a dashed faint line and the words "Extraction in progress" in place of numbers.

### Code Block
A glass card holding mono text at 13px and 1.9 line-height, horizontally scrollable. Used for real commands and real model output only.

### Phrase Marquee
One strip per page: display-face phrases at 1.875rem to 3rem with their counts in muted tabular figures, between two hairlines, moving linearly over 70s. It pauses on hover and becomes a static, manually scrollable strip under reduced motion.

## Do's and Don'ts

### Do:
- **Do** reserve warm and cool for risk direction, and put a text label or key next to every use.
- **Do** use paper for every interface accent: primary fill, focus outline, selection, monochrome data marks.
- **Do** set measured numbers in Satoshi with tabular lining figures, and give every chart value as text beside or below the chart.
- **Do** keep the three radii by role: 20px cards, full-pill controls, 12px inputs.
- **Do** add word-spacing of 0.14em wherever the display face is used.
- **Do** use the single ease-out curve (0.23, 1, 0.32, 1) for entrances, once per element, and route every animation through `useCalm` so reduced motion gets settled content.
- **Do** open each section directly with its headline, left-aligned on the content edge, with the measure capped in `ch`.
- **Do** show unfinished results as a dashed faint mark with a plain sentence, never as a placeholder number.

### Don't:
- **Don't** use warm or cool for buttons, links, borders, highlights or any other decoration.
- **Don't** introduce a third hue; greys are paper at reduced alpha or the muted and faint tiers.
- **Don't** set running numbers, labels or headings in the mono face; it is for JSON, column names, commands and paths.
- **Don't** put a shadow on anything but the frosted card.
- **Don't** animate layout properties for entrances; move with transform, opacity and blur, and let state changes fade colour only.
- **Don't** add moving or coloured elements to the field that do not correspond to data, or show the field without its key.
- **Don't** hide content behind an animation that may not run; everything is visible by default.

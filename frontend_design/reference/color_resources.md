# Color System Reference

## Purpose

Use this file to create intentional, accessible, product-specific color systems.

Never choose colors randomly.

---

# 1. COLOR SYSTEM

Every serious project should define semantic colors.

Minimum:

```text
Background
Foreground
Primary
Primary foreground
Secondary
Secondary foreground
Muted
Muted foreground
Border
Success
Warning
Error
```

---

# 2. COLOR SELECTION PROCESS

Use:

```text
Product personality
↓
Brand direction
↓
Dominant color
↓
Supporting colors
↓
Neutral scale
↓
Semantic states
↓
Contrast check
```

---

# 3. DOMINANT COLOR

The dominant color should support the product personality.

Examples:

```text
Finance → navy / deep neutral
Healthcare → calm blue / teal / green
Nature → green / earth tones
Luxury → black / cream / restrained accent
Education → friendly but readable colors
Gaming → stronger contrast
Developer tools → neutral + controlled accent
Creative agency → distinctive accent palette
```

These are starting points, not rules.

---

# 4. NEUTRALS

Do not default to pure:

```text
#000000
#FFFFFF
```

unless the design specifically calls for it.

Consider:

```text
Warm white
Cool white
Off-white
Charcoal
Slate
Warm gray
Cool gray
```

Neutrals often determine whether a design feels premium or generic.

---

# 5. ACCENT

Accent colors should highlight:

* CTA
* Important information
* Selected state
* Links
* Status
* Key metrics

Do not make every element an accent.

---

# 6. 60/30/10

Use as a starting principle:

```text
60% dominant
30% secondary
10% accent
```

Do not treat this as a strict formula.

---

# 7. DARK MODE

Dark mode should not simply be:

```text
background: #000;
text: #fff;
```

Consider:

```text
Near-black background
Layered surfaces
Muted borders
Readable secondary text
Controlled accent
```

Use elevation through subtle differences in surfaces.

---

# 8. GRADIENTS

Gradients can be used for:

* Hero
* Background
* Accent
* Image overlays
* Brand identity

Avoid excessive gradient usage.

Do not use:

```text
gradient background
+
gradient heading
+
gradient button
+
gradient border
```

all at once.

---

# 9. SEMANTIC COLORS

Success:

```text
Green or appropriate positive color
```

Warning:

```text
Amber / yellow
```

Error:

```text
Red
```

Information:

```text
Blue or appropriate informational color
```

Do not rely only on color.

Pair status with:

* Icon
* Text
* Shape
* Pattern

when necessary.

---

# 10. CONTRAST

Check text and interactive elements for sufficient contrast.

Important:

Do not sacrifice readability for minimalism.

Avoid:

```text
Light gray text
on
slightly lighter gray background
```

simply because it looks subtle.

---

# 11. COLOR TOOLS

Useful references:

```text
Coolors
Adobe Color
Color Hunt
Happy Hues
ColorBox
Huetone
ColorBrewer
Web Gradients
```

Use accessible palette tools when building data visualizations or complex systems.

---

# 12. DATA VISUALIZATION

Do not use many random colors.

Use:

```text
Primary series
Secondary series
Comparison series
Positive
Negative
Neutral
```

Color should communicate meaning.

---

# 13. COLOR CONSISTENCY

Once selected, define tokens.

Example:

```css
:root {
    --background: ...;
    --foreground: ...;
    --primary: ...;
    --secondary: ...;
    --muted: ...;
    --border: ...;
    --success: ...;
    --warning: ...;
    --error: ...;
}
```

Components should use semantic tokens rather than random hex values.

---

# 14. COLOR ANTI-PATTERNS

Avoid:

* Random hex values throughout CSS
* Too many accent colors
* Low-contrast text
* Excessive neon
* Excessive gradients
* Rainbow UI
* Color without semantic meaning

---

# 15. FINAL COLOR TEST

Ask:

```text
Does the palette fit the product?
Is the hierarchy clear?
Is the CTA obvious?
Is text readable?
Are semantic states understandable?
Does the interface still work without color?
Does the palette feel distinctive?
```

# Typography Reference

## Purpose

Typography should establish hierarchy, readability, and personality.

Do not treat fonts as decoration.

---

# 1. FONT COUNT

Default:

```text
1 primary family
+
1 optional display family
```

Avoid unnecessary font combinations.

---

# 2. TYPOGRAPHIC HIERARCHY

Define:

```text
Display
H1
H2
H3
Body
Small
Caption
```

Each should have a clear purpose.

---

# 3. DISPLAY TYPOGRAPHY

Use for:

* Hero headlines
* Large statements
* Creative portfolios
* Editorial designs

Display text may have stronger personality.

---

# 4. BODY TYPOGRAPHY

Prioritize:

* Readability
* Comfortable line-height
* Appropriate width
* Strong contrast

Target approximately:

```text
45–80 characters per line
```

for comfortable reading.

---

# 5. FONT PAIRING

Good pairing principles:

```text
Sans + Sans
Sans + Serif
Display + Neutral
Mono + Sans
```

The fonts should have a reason to coexist.

---

# 6. COMMON DIRECTIONS

## Modern SaaS

Use:

* Clean sans-serif
* Strong weight hierarchy
* Comfortable body text

## Editorial

Use:

* Serif or expressive display
* Strong typography
* Generous whitespace

## Developer

Use:

* Sans for UI
* Monospace for code

Do not use monospace for the entire interface unless intentional.

## Luxury

Use:

* Elegant serif
* Refined sans
* Restrained weights

## Creative

Can use:

* Experimental display fonts
* Strong scale differences
* Unusual compositions

Maintain readability.

---

# 7. WEIGHT

Common:

```text
400 → Regular
500 → Medium
600 → Semibold
700 → Bold
```

Do not use every available weight.

---

# 8. LINE HEIGHT

Headings:

Use tighter line-height.

Body:

Use comfortable line-height.

Avoid extremely tight body text.

---

# 9. LETTER SPACING

Useful for:

* Uppercase labels
* Small metadata
* Display typography

Do not overuse negative tracking.

---

# 10. FONT RESOURCES

Useful references:

```text
Google Fonts
Fontshare
Adobe Fonts
Fontjoy
Type Scale
Typewolf
Typespiration
```

When selecting a font, consider:

* Licensing
* Language support
* Weight availability
* Performance
* Readability

---

# 11. RESPONSIVE TYPOGRAPHY

Large typography should scale.

Possible approach:

```css
font-size: clamp(
    2.5rem,
    6vw,
    6rem
);
```

Do not blindly use the same font size across devices.

---

# 12. TYPOGRAPHY ANTI-PATTERNS

Avoid:

* Too many fonts
* Tiny body text
* Excessive uppercase
* Poor line length
* Extremely thin text
* Random font weights
* Huge headings with no hierarchy
* Poor mobile scaling

---

# 13. FINAL TYPOGRAPHY TEST

Ask:

```text
Can I understand the hierarchy immediately?
Is body text comfortable?
Does the typography match the brand?
Does mobile remain readable?
Are headings too large?
Are secondary texts too faint?
```

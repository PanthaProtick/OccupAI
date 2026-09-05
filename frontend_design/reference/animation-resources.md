# Animation & Interaction Reference

## Purpose

Use this file when adding motion, transitions, micro-interactions, scroll effects, or complex animation.

Animation must improve communication, hierarchy, feedback, or personality.

Never animate something simply because it can be animated.

---

# 1. Animation Hierarchy

Use this order:

```text
CSS
↓
Native browser APIs
↓
Motion / Framer Motion
↓
GSAP
↓
Three.js / WebGL
```

Choose the simplest appropriate technology.

---

# 2. CSS TRANSITIONS

Default solution for:

* Buttons
* Links
* Hover states
* Focus states
* Cards
* Inputs
* Small transforms

Example:

```css
.element {
    transition:
        transform 200ms ease,
        opacity 200ms ease,
        background-color 200ms ease;
}
```

---

# 3. CSS KEYFRAMES

Use for:

* Loaders
* Pulsing indicators
* Simple entrances
* Repeating decorative motion

Avoid infinite animation unless it communicates an ongoing state.

---

# 4. Motion / Framer Motion

Use for React projects when you need:

* Component transitions
* Enter/exit animations
* Layout animation
* Gesture interaction
* Shared layout transitions

Good for:

```text
Modal
Drawer
Tabs
Accordion
Page transition
Animated cards
```

---

# 5. GSAP

Use for:

* Complex timelines
* Scroll-driven experiences
* Advanced sequencing
* Precise animation control
* Creative landing pages

Do not use GSAP for a simple button hover.

---

# 6. Lottie

Use for:

* Product illustrations
* Animated icons
* Empty states
* Onboarding
* Explanatory visuals

Avoid large animations that significantly increase page weight.

---

# 7. Three.js / WebGL

Use only when 3D meaningfully contributes to:

* Product visualization
* Brand experience
* Scientific visualization
* Gaming
* Interactive 3D

Do not use WebGL merely because it looks impressive.

---

# 8. Animation Categories

## Micro-interaction

Typical duration:

```text
100–250ms
```

Examples:

* Button hover
* Icon movement
* Checkbox
* Toggle
* Input focus

---

## Component animation

Typical duration:

```text
200–400ms
```

Examples:

* Dropdown
* Modal
* Drawer
* Accordion
* Tooltip
* Tab transition

---

## Page animation

Typical duration:

```text
400–800ms
```

Use sparingly.

---

# 9. EASING

Prefer natural motion.

Good:

```text
ease-out
ease-in-out
custom cubic-bezier
spring-based motion
```

Avoid using linear animation for most UI interactions.

---

# 10. HOVER PATTERNS

Useful patterns:

### Lift

```css
transform: translateY(-4px);
```

### Scale

Use subtle scale.

### Glow

Use only for suitable visual styles.

### Image zoom

Good for:

* Product cards
* Portfolio projects
* Photography

### Icon movement

Good for:

* Arrow buttons
* Navigation
* CTAs

---

# 11. SCROLL REVEALS

Use for:

* Section entrances
* Portfolio projects
* Feature blocks
* Images

Avoid:

```text
Every element fades in
+
Every element slides
+
Every element has different delay
```

This creates visual noise.

---

# 12. STAGGER

Stagger is useful for:

* Lists
* Cards
* Navigation items
* Feature groups

Keep delays short.

---

# 13. PARALLAX

Use only when:

* The design is editorial
* The website is highly visual
* Depth improves storytelling

Avoid excessive parallax on mobile.

---

# 14. PAGE TRANSITIONS

Use for:

* Creative portfolios
* Agencies
* Experimental marketing sites

Avoid unnecessary transitions in:

* Dashboards
* Admin systems
* Productivity tools

Users often want speed in functional applications.

---

# 15. ANIMATION ANTI-PATTERNS

Avoid:

* Constant bouncing
* Excessive zoom
* Excessive blur
* Random floating objects
* Infinite movement everywhere
* Long loading animations
* Animations that block interaction
* Excessive cursor effects
* Heavy WebGL without purpose

---

# 16. REDUCED MOTION

Always support:

```css
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
}
```

---

# 17. ANIMATION RESOURCE TYPES

Useful references include:

```text
GSAP
Motion
Framer Motion
LottieFiles
Animate.css
Hover.css
React Bits
Magic UI
Aceternity UI
UIverse
```

Use them according to the project.

---

# 18. FINAL ANIMATION TEST

Before adding animation, ask:

```text
Does it communicate something?
Does it improve feedback?
Does it improve hierarchy?
Does it improve continuity?
Does it reinforce brand personality?
Does it justify its performance cost?
```

If the answer is no:

Do not add it.

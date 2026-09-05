---

name: frontend-design
description: Creates high-quality, distinctive, modern, responsive frontend interfaces for websites and web applications. Use this skill whenever designing, redesigning, implementing, or improving frontend UI, including portfolios, SaaS products, landing pages, dashboards, e-commerce, AI products, developer tools, agencies, blogs, education, healthcare, finance, restaurants, and other web experiences. Applies design reasoning, visual direction, typography, color systems, layout, components, responsive design, accessibility, interaction, animation, micro-interactions, and performance. Consult the skill's references and examples when appropriate. Avoids generic AI-generated UI and chooses design decisions based on the product, audience, and purpose.
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Frontend Design Skill

## 1. ROLE

Act as a senior:

* Product designer
* UI/UX designer
* Visual designer
* Frontend engineer
* Interaction designer

Your responsibility is not merely to write frontend code.

Your responsibility is to create a frontend experience that is:

* Visually distinctive
* Usable
* Responsive
* Accessible
* Consistent
* Interactive
* Performant
* Appropriate for the product
* Production-ready

The final result should look intentionally designed rather than automatically generated.

---

# 2. PRIMARY PRINCIPLE

Never start with:

> "What looks cool?"

Start with:

> "What design best communicates this product and helps the user accomplish their goal?"

Follow this process:

```text
Understand the product
        ↓
Understand the user
        ↓
Identify the primary goal
        ↓
Identify the website category
        ↓
Choose visual direction
        ↓
Create design system
        ↓
Design information hierarchy
        ↓
Choose components
        ↓
Choose interaction
        ↓
Choose animation
        ↓
Implement responsively
        ↓
Check accessibility
        ↓
Check performance
        ↓
Review visual quality
```

---

# 3. ANTI-GENERIC DESIGN RULE

Do not produce a generic AI-generated website.

Do NOT automatically combine:

* Dark navy background
* Purple/blue gradient
* Giant white heading
* Glassmorphism
* Rounded cards
* Glowing buttons
* Floating gradient blobs
* Particle backgrounds
* Excessive shadows
* Excessive animations

This style is allowed when it genuinely fits the product.

It is forbidden as a default.

Every major visual decision should have a reason.

---

# 4. USE THE REFERENCE LIBRARY

This skill may contain:

```text
references/
examples/
assets/
```

Use them intelligently.

Before implementing a complex or visually important UI, consult the relevant reference.

Examples:

```text
references/design-resources.md
references/animation-resources.md
references/color-resources.md
references/typography-resources.md
references/ui-patterns.md
references/website-types.md
```

Examples may contain:

```text
examples/portfolio.md
examples/saas.md
examples/dashboard.md
examples/ecommerce.md
examples/landing-page.md
```

Do not read every reference file unnecessarily.

Read the relevant reference based on the current task.

---

# 5. REFERENCE USAGE RULE

References are inspiration and implementation guidance.

Do not blindly copy a design.

Instead:

```text
Reference
   ↓
Understand pattern
   ↓
Adapt to current product
   ↓
Create consistent implementation
```

The final interface must still have its own visual identity.

---

# 6. FIRST: UNDERSTAND THE PRODUCT

Before writing UI code, determine:

### Product

What is being built?

### Audience

Who will use it?

### Goal

What should the user accomplish?

### Context

Where and how will the product be used?

### Personality

Should it feel:

* Professional?
* Friendly?
* Premium?
* Technical?
* Creative?
* Futuristic?
* Minimal?
* Energetic?
* Trustworthy?
* Playful?

### Primary CTA

What is the most important action?

Examples:

```text
Get Started
Book a Demo
View Projects
Buy Now
Create Account
Upload File
Analyze Data
Contact Me
```

---

# 7. WEBSITE CATEGORY

Identify the closest category.

Possible categories include:

```text
Portfolio
Personal Website
SaaS
Landing Page
Startup
AI Product
Developer Tool
Dashboard
Admin Panel
E-commerce
Marketplace
Agency
Restaurant
Finance
Healthcare
Education
Blog
Magazine
Documentation
Gaming
Social Platform
Community
Productivity
Analytics
Travel
Real Estate
Event
Non-profit
```

If the project does not fit one category, identify the closest combination.

---

# 8. CATEGORY-SPECIFIC DESIGN

## Portfolio

Prioritize:

* Personal identity
* Projects
* Experience
* Skills
* About
* Contact

Possible directions:

* Editorial
* Minimal
* Creative
* Experimental
* Developer-focused

Do not make it look like a generic resume.

---

## SaaS

Prioritize:

* Value proposition
* Product explanation
* Product visuals
* Features
* Social proof
* Pricing
* CTA

Design should communicate trust and product clarity.

---

## AI Product

Possible directions:

* Futuristic
* Scientific
* Technical
* Minimal
* Premium

Use controlled:

* Gradients
* Glow
* Data visualization
* Interactive demonstrations
* Status animations

Do not assume every AI product needs a neon purple interface.

---

## Dashboard

Prioritize:

* Information hierarchy
* Navigation
* Data
* Filters
* Tables
* Charts
* Status

Do not turn every piece of information into a card.

Use whitespace and grouping intelligently.

---

## E-commerce

Prioritize:

* Product imagery
* Price
* Product information
* Search
* Filters
* Cart
* Checkout
* Reviews

Animation should improve shopping feedback.

---

## Developer Tool

Prioritize:

* Documentation
* Code
* Search
* Navigation
* Technical clarity

Use:

* Monospace selectively
* Code blocks
* Terminal patterns
* Keyboard shortcuts

Avoid unnecessary decoration.

---

## Agency

Can use:

* Large typography
* Creative layouts
* Strong imagery
* Case studies
* Page transitions
* Scroll animations

Motion may be more expressive but must remain purposeful.

---

## Finance

Prioritize:

* Trust
* Numbers
* Readability
* Data
* Clear actions

Avoid excessive visual effects.

---

## Healthcare

Prioritize:

* Accessibility
* Trust
* Clarity
* Readability
* Simple navigation

Never sacrifice usability for visual style.

---

## Restaurant

Prioritize:

* Food photography
* Atmosphere
* Menu
* Reservation
* Location
* Opening hours

Visual storytelling is important.

---

## Education

Prioritize:

* Learning paths
* Courses
* Progress
* Search
* Clear actions

Design should feel approachable.

---

## Gaming

Can use:

* Dramatic typography
* Strong imagery
* High contrast
* Motion
* Interactive backgrounds

But maintain navigation clarity.

---

# 9. VISUAL DIRECTION

Select ONE primary visual direction.

Possible directions:

```text
Minimal
Editorial
Luxury
Corporate
Technical
Futuristic
Creative
Experimental
Brutalist
Neo-brutalist
Playful
Friendly
Cinematic
Retro
Gaming
Data-focused
Organic
Industrial
Elegant
```

A secondary style may be used if it complements the primary style.

Do not randomly combine unrelated styles.

---

# 10. DESIGN SYSTEM FIRST

Before building many components, establish:

```text
Colors
Typography
Spacing
Grid
Radius
Borders
Shadows
Buttons
Inputs
Cards
Motion
Icons
```

For larger applications, use design tokens.

Example:

```css
:root {
    --color-background: ...;
    --color-foreground: ...;
    --color-primary: ...;
    --color-secondary: ...;
    --color-muted: ...;
    --color-border: ...;

    --space-xs: ...;
    --space-sm: ...;
    --space-md: ...;
    --space-lg: ...;
    --space-xl: ...;

    --radius-sm: ...;
    --radius-md: ...;
    --radius-lg: ...;
}
```

---

# 11. COLOR

Never choose colors independently for each component.

Create a semantic palette.

At minimum:

```text
Background
Foreground
Primary
Secondary
Muted
Border
Success
Warning
Error
```

Use color according to the product.

Do not automatically use:

```text
purple + blue + black
```

for technology products.

---

# 12. COLOR BALANCE

Use the 60/30/10 principle as a starting point:

```text
60% dominant/background
30% secondary surfaces
10% accent
```

This is a guideline, not a strict rule.

The goal is visual hierarchy.

---

# 13. TYPOGRAPHY

Typography should communicate personality and hierarchy.

Normally use:

```text
1 primary font family
+
1 optional secondary/display font
```

Establish:

```text
Display
H1
H2
H3
Body
Small
Caption
```

Avoid using many unrelated fonts.

Body text must remain comfortable to read.

Do not use extremely thin fonts for important information.

---

# 14. LAYOUT

Use a deliberate layout system.

Common patterns:

```text
Single column
Two column
Three column
Four column
12-column grid
Editorial grid
Asymmetric composition
```

Do not center everything.

Do not put everything inside cards.

Use whitespace intentionally.

---

# 15. SPACING

Use a consistent spacing scale.

A useful starting point:

```text
8
16
24
32
48
64
96
128
```

Adapt according to the design.

Avoid arbitrary spacing values unless there is a specific reason.

---

# 16. CONTAINERS

Use an appropriate maximum width.

Example:

```css
.container {
    width: min(1200px, calc(100% - 32px));
    margin-inline: auto;
}
```

Adjust based on the project.

Do not make content unnecessarily wide.

---

# 17. INFORMATION HIERARCHY

Every page must communicate:

```text
What is this?
↓
Why does it matter?
↓
What should I look at?
↓
What should I do?
```

Use:

* Typography
* Position
* Size
* Contrast
* Whitespace
* Color

to establish hierarchy.

---

# 18. HERO SECTION

A hero should normally communicate:

```text
What
+
Why
+
Action
```

Possible structure:

```text
Eyebrow
Headline
Supporting text
Primary CTA
Secondary CTA
Visual
```

Do not use vague marketing copy unless the brand genuinely calls for it.

---

# 19. COMPONENT DESIGN

Create reusable components.

Typical components:

```text
Navbar
Hero
Button
Card
Badge
Section
Input
Modal
Dropdown
Tabs
Accordion
Table
Footer
```

Reuse components where appropriate.

Do not create one enormous universal component.

---

# 20. CARDS

Cards should group related information.

Good uses:

```text
Product
Project
Feature
Pricing plan
Statistic
Article
User
```

Do not put every section into a card.

Avoid:

```text
card
  ↓
card
  ↓
card
```

without meaningful grouping.

---

# 21. BORDER RADIUS

Use a coherent radius system.

Example:

```text
Small → 6px
Medium → 10px
Large → 16px
Extra Large → 24px
```

The actual values should match the visual direction.

Do not automatically use extremely rounded corners everywhere.

---

# 22. SHADOWS

Use shadows to communicate elevation.

Prefer subtle shadows.

If the design is flat/minimal, use borders instead.

Do not put huge shadows around every component.

---

# 23. GLASSMORPHISM

Glassmorphism is optional.

Use only when appropriate.

Good:

* Floating navigation
* Overlay controls
* Futuristic interfaces
* Premium interfaces

Bad:

* Every card
* Every section
* Every button

---

# 24. GRADIENTS

Gradients are optional.

Good uses:

* Hero background
* Accent
* Image overlay
* Subtle glow
* Brand identity

Do not use gradients on everything.

---

# 25. BUTTON HIERARCHY

Define:

```text
Primary
Secondary
Tertiary
Destructive
```

The primary action should visually dominate.

Do not make every button equally strong.

---

# 26. INTERACTION STATES

Interactive elements should have:

```text
Default
Hover
Focus
Active
Disabled
Loading
Error
Success
```

Never design only the default state.

---

# 27. HOVER

Good hover effects:

```text
Small translation
Subtle scale
Color transition
Border transition
Shadow transition
Icon movement
Image zoom
Underline animation
```

Keep them controlled.

Avoid dramatic movement that makes interfaces feel unstable.

---

# 28. ANIMATION PHILOSOPHY

Animation should communicate:

```text
Feedback
Hierarchy
Continuity
State
Spatial relationship
```

Animation should not exist merely to show technical ability.

---

# 29. ANIMATION LEVELS

## Micro interaction

Examples:

* Button hover
* Icon movement
* Toggle
* Focus
* Card hover

Typical duration:

```text
100–250ms
```

## Component animation

Examples:

* Modal
* Dropdown
* Sidebar
* Tabs
* Accordion

Typical duration:

```text
200–400ms
```

## Page animation

Examples:

* Hero entrance
* Section reveal
* Page transition

Typical duration:

```text
400–800ms
```

Use carefully.

---

# 30. ANIMATION TECHNOLOGY

Choose the simplest appropriate solution.

### CSS

Use for:

* Hover
* Focus
* Simple transitions
* Simple keyframes

### Motion / Framer Motion

Use for:

* React component transitions
* Layout animation
* Gestures
* Presence animations

### GSAP

Use for:

* Complex timelines
* Advanced scroll animation
* Precise sequencing

### Lottie

Use for:

* Animated illustrations
* Product animation
* Animated icons

### Three.js / WebGL

Use only when 3D provides meaningful value.

Never introduce a heavy animation library for a simple hover effect.

---

# 31. SCROLL ANIMATION

Use scroll animation selectively.

Possible effects:

```text
Fade
Slide
Scale
Parallax
Text reveal
Image reveal
```

Do not animate every element independently.

If everything moves, nothing feels important.

---

# 32. REDUCED MOTION

Respect user preferences.

Implement:

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

# 33. NAVIGATION

Navigation should be immediately understandable.

Desktop:

```text
Logo
Navigation
Secondary action
Primary CTA
```

Mobile:

```text
Logo
Menu
```

Avoid excessive navigation items.

---

# 34. FORMS

Every form field should have:

```text
Label
Input
Focus state
Validation
Error state
Success state where relevant
```

Do not rely only on placeholders.

Use semantic input types.

---

# 35. LOADING

Applications should consider:

```text
Initial loading
Skeleton
Spinner
Empty state
Error state
Success state
```

Do not leave the user staring at a blank screen.

---

# 36. EMPTY STATES

Explain:

```text
What happened
Why it matters
What the user can do
```

Example:

```text
No projects yet.

Create your first project to start tracking your work.

[Create Project]
```

---

# 37. ERROR STATES

Errors should be:

* Specific
* Understandable
* Actionable

Avoid generic messages when useful information is available.

---

# 38. RESPONSIVE DESIGN

Responsive design is not simply shrinking desktop.

For every breakpoint consider:

```text
Navigation
Typography
Spacing
Columns
Images
Tables
Cards
Buttons
Interactions
```

Possible breakpoints:

```text
~640px
~768px
~1024px
~1280px
```

Use content-driven breakpoints when appropriate.

---

# 39. MOBILE

On mobile:

* Simplify navigation
* Stack layouts where appropriate
* Maintain readable typography
* Maintain sufficient touch targets
* Avoid horizontal overflow
* Preserve hierarchy
* Remove unnecessary decoration if it harms usability

Do not simply compress desktop UI.

---

# 40. ACCESSIBILITY

Always consider:

* Semantic HTML
* Keyboard navigation
* Focus states
* Screen readers
* Color contrast
* Alt text
* Reduced motion
* Form labels
* Button semantics

Prefer:

```html
<button>
```

over:

```html
<div onclick="">
```

when implementing an action.

---

# 41. ICONS

Use one coherent icon system.

Avoid randomly mixing icon families.

Icons should:

* Support meaning
* Maintain consistent stroke/weight
* Have appropriate sizing
* Have accessible labels when needed

---

# 42. IMAGES

Use images intentionally.

Possible image types:

```text
Product screenshots
Photography
Illustrations
Diagrams
Textures
Generated visuals
```

Never use random imagery merely to fill empty space.

---

# 43. CONTENT

Use realistic content.

Avoid excessive:

```text
Lorem ipsum
Lorem ipsum
Lorem ipsum
```

When the product context is known, create realistic UI copy.

Content should demonstrate the actual product.

---

# 44. CTA

Use one dominant CTA per major section when appropriate.

Avoid competing CTAs.

The primary action should be obvious.

---

# 45. PERFORMANCE

Do not sacrifice performance for visual effects.

Avoid unnecessary:

* Large images
* Heavy JavaScript
* Multiple animation libraries
* Huge dependencies
* Unoptimized assets
* Excessive DOM complexity

Prefer CSS for simple effects.

---

# 46. VANILLA HTML/CSS/JS

For vanilla projects:

Use:

```text
Semantic HTML
Modern CSS
CSS variables
Grid
Flexbox
Modular JavaScript
Accessible interactions
```

Keep structure understandable.

---

# 47. REACT

For React:

Prefer:

```text
Reusable components
Composition
Props
Local state
Clear state ownership
Semantic HTML
Design tokens
```

Avoid:

* Giant components
* Repeated JSX
* Unnecessary global state
* Excessive useEffect
* Over-abstraction

---

# 48. TAILWIND

When using Tailwind:

* Maintain spacing consistency
* Use responsive utilities
* Extract repeated components
* Use design tokens where appropriate
* Avoid excessive arbitrary values

Avoid unnecessary patterns such as:

```text
mt-[37px]
px-[19px]
text-[23px]
```

when existing design tokens are sufficient.

---

# 49. DESIGN REFERENCE WORKFLOW

When the project needs strong visual design:

### Step 1

Identify the website category.

### Step 2

Read the appropriate website-type reference.

### Step 3

Read relevant color and typography references.

### Step 4

Read UI pattern references.

### Step 5

Read animation references if animation is important.

### Step 6

Choose a coherent visual direction.

### Step 7

Implement.

### Step 8

Compare the implementation against the reference patterns.

### Step 9

Improve the weak areas.

Do not blindly reproduce reference designs.

---

# 50. DESIGN INSPIRATION VS IMPLEMENTATION

Separate:

```text
Inspiration
```

from:

```text
Implementation
```

A visually impressive example does not necessarily mean its implementation should be copied.

Prefer:

```text
Understand visual principle
→
Adapt it
→
Implement appropriately
```

---

# 51. AVOID DESIGN CLICHÉS

Do not overuse:

* Gradient blobs
* Glassmorphism
* Neon glow
* Particle backgrounds
* Floating cards
* Infinite marquees
* Cursor-following effects
* Giant rounded containers
* Excessive parallax
* Excessive 3D
* Excessive page transitions

Use them only when they strengthen the product.

---

# 52. PERSONALITY

The interface should have personality appropriate to the product.

Ask:

> What should users remember about this interface?

Possible answers:

```text
Elegant
Fast
Technical
Trustworthy
Creative
Friendly
Premium
Bold
Calm
Powerful
Playful
```

Use visual choices to reinforce that personality.

---

# 53. CONSISTENCY

Maintain consistency in:

```text
Typography
Colors
Spacing
Radius
Borders
Shadows
Icons
Buttons
Animations
```

Do not randomly change styles between sections.

---

# 54. PROGRESSIVE COMPLEXITY

Start simple.

Only introduce complexity when necessary.

For example:

```text
Simple CSS transition
```

before:

```text
GSAP timeline
```

and:

```text
Static visual
```

before:

```text
WebGL scene
```

unless the product specifically requires the advanced solution.

---

# 55. DO NOT OVER-DESIGN

A polished interface does not need every possible effect.

If removing an effect makes the interface clearer, remove it.

If adding an effect does not improve:

```text
Understanding
Feedback
Navigation
Brand
Hierarchy
```

do not add it.

---

# 56. DESIGN REVIEW

Before finishing, inspect the result critically.

Ask:

### Visual

* Does it look intentionally designed?
* Does it have a clear visual identity?
* Does it avoid generic AI patterns?

### Hierarchy

* Is the most important information obvious?
* Is the CTA obvious?

### Typography

* Is the hierarchy clear?
* Is body text readable?

### Color

* Is the palette coherent?
* Is contrast sufficient?

### Layout

* Is spacing consistent?
* Is alignment intentional?

### Interaction

* Do interactive elements communicate their states?

### Animation

* Does animation have a purpose?
* Is there too much motion?

### Responsive

* Does mobile feel intentionally designed?
* Does tablet work?
* Does desktop work?

### Accessibility

* Can the interface be keyboard navigated?
* Are focus states visible?
* Are semantic elements used?
* Is reduced motion supported?

### Performance

* Are there unnecessary dependencies?
* Are assets optimized?
* Is animation unnecessarily expensive?

---

# 57. FINAL QUALITY GATE

Do not consider the frontend finished until these are true:

```text
[ ] Product purpose is clear
[ ] Website category was identified
[ ] Visual direction is intentional
[ ] Color system is coherent
[ ] Typography is coherent
[ ] Layout has clear hierarchy
[ ] Components are reusable
[ ] Buttons have proper hierarchy
[ ] Interactive states exist
[ ] Animation is purposeful
[ ] Reduced motion is supported
[ ] Mobile is intentionally designed
[ ] Tablet works
[ ] Desktop works
[ ] Accessibility was considered
[ ] Loading states exist where necessary
[ ] Empty states exist where necessary
[ ] Error states exist where necessary
[ ] No unnecessary visual effects
[ ] No unnecessary dependencies
[ ] No obvious generic AI patterns
[ ] No major duplicated UI code
[ ] Final result feels product-specific
```

---

# 58. PRIORITY ORDER

When design decisions conflict, use this priority:

```text
1. Usability
2. Accessibility
3. Information hierarchy
4. Responsive behavior
5. Performance
6. Visual consistency
7. Brand personality
8. Interaction
9. Animation
10. Decoration
```

Never sacrifice the first items for the last items.

---

# 59. CORE RULE

The goal is NOT:

> Make the website fancy.

The goal is:

> Create a distinctive, coherent, responsive interface where typography, layout, color, components, interaction, and animation work together to communicate the product clearly and provide an excellent user experience.

Always ask:

> Why is this design decision here?

If there is no good answer:

**Remove it.**

---

# 60. EXECUTION SUMMARY

For every frontend task:

```text
1. Understand the product
2. Identify the audience
3. Identify the primary user goal
4. Identify the website category
5. Choose a visual direction
6. Consult relevant references
7. Establish typography
8. Establish color tokens
9. Establish spacing and layout
10. Design information hierarchy
11. Build reusable components
12. Add interaction states
13. Add purposeful animation
14. Implement responsive behavior
15. Implement accessibility
16. Optimize performance
17. Review critically
18. Remove unnecessary complexity
19. Verify against the quality checklist
20. Deliver production-quality frontend
```

Never skip directly from:

```text
Prompt
↓
Code
```

Use:

```text
Prompt
↓
Design reasoning
↓
Reference
↓
Design system
↓
Implementation
↓
Review
↓
Refinement
```

This is the standard for every frontend project.

# Frontend Design Resource Index

## Purpose

This file is a curated index of external resources that can help with frontend design decisions.

Do not browse or use every resource for every project.

Select resources according to the current task.

---

# 1. Resource Selection Strategy

Use this decision tree:

```text
Need visual inspiration?
→ Design inspiration resources

Need UI component?
→ UI component resources

Need animation?
→ Animation resources

Need colors?
→ Color resources

Need typography?
→ Typography resources

Need layout?
→ Layout / UI pattern resources

Need icons?
→ Icon resources

Need accessibility guidance?
→ Design system / accessibility resources
```

Do not add external dependencies simply because a resource exists.

---

# 2. UI COMPONENT RESOURCES

## shadcn/ui

Use when:

* Building React applications
* Using Tailwind CSS
* Need accessible, customizable primitives
* Need a strong production foundation

Best for:

* Forms
* Dialogs
* Dropdowns
* Tables
* Navigation
* Buttons
* Cards
* Inputs

Principle:

Use components as a foundation, then customize the visual language.

Do not make every project look identical to shadcn/ui.

---

## Aceternity UI

Use when:

* Creative landing pages
* Marketing websites
* Premium SaaS
* AI products
* Interactive hero sections

Good for:

* Animated backgrounds
* Hero sections
* Cards
* Text effects
* Interactive components

Use selectively.

---

## React Bits

Use when:

* React projects
* Need visually interesting components
* Need animation examples
* Need copyable UI patterns

Good for:

* Text animation
* Buttons
* Cards
* Backgrounds
* Navigation
* Interactive components

---

## Magic UI

Use when:

* Modern React/Tailwind applications
* SaaS
* AI products
* Marketing websites

Good for:

* Animated components
* Marquees
* Text effects
* Backgrounds
* Interactive elements

Avoid using too many animated components simultaneously.

---

## Radix UI

Use when:

* Accessibility is important
* Building custom design systems
* Need reliable primitives

Good for:

* Dialog
* Popover
* Tooltip
* Dropdown
* Tabs
* Accordion
* Select

Prefer primitives when the project requires strong customization.

---

## Headless UI

Use when:

* React
* Tailwind
* Accessible unstyled components
* Custom visual design

---

## Uiverse

Use for:

* Button inspiration
* CSS effects
* Small interactive elements
* Experimental ideas

Treat it primarily as an inspiration source.

Do not automatically copy its visual style into the entire application.

---

# 3. ICON RESOURCES

## Lucide

Default choice for many modern applications.

Good for:

* SaaS
* Dashboards
* Developer tools
* Portfolios
* Productivity applications

Advantages:

* Consistent
* Clean
* Customizable
* Large collection

---

## Heroicons

Good for:

* Tailwind projects
* SaaS
* Admin interfaces
* Clean applications

---

## Tabler Icons

Good for:

* Dashboards
* Data-heavy interfaces
* Technical products

---

## Simple Icons

Use when official brand logos are required.

---

# 4. DESIGN SYSTEM REFERENCES

## Material Design

Use for:

* General interaction principles
* Accessibility
* Components
* Responsive behavior

Do not blindly impose Material Design on every project.

---

## Apple Human Interface Guidelines

Use for:

* Interaction principles
* Motion
* Clarity
* Hierarchy
* Touch interfaces

---

## IBM Carbon

Use for:

* Enterprise interfaces
* Data-heavy applications
* Complex workflows

---

# 5. DESIGN INSPIRATION

## Awwwards

Use for:

* High-end marketing websites
* Creative agency websites
* Experimental interaction

Do not copy award-site complexity into normal applications.

---

## Godly

Use for:

* Modern web inspiration
* Creative websites
* Interaction ideas

---

## Mobbin

Use for:

* Product UX
* Mobile patterns
* Navigation
* Onboarding
* Real-world UI flows

---

## BentoGrids

Use for:

* Bento layouts
* Portfolio sections
* Product feature sections
* Dashboard compositions

---

## Landingfolio

Use for:

* Landing pages
* SaaS
* Marketing sections
* Hero patterns

---

## SiteInspire

Use for:

* General website inspiration
* Layout
* Typography
* Branding

---

## Dribbble

Use for:

* Visual inspiration
* UI concepts
* Component ideas

Important:

Dribbble designs are often concepts rather than production-ready UX.

Do not copy unrealistic interaction patterns without evaluating usability.

---

## Behance

Use for:

* Branding
* Visual systems
* Editorial design
* Creative direction

---

# 6. BACKGROUNDS AND VISUAL EFFECTS

## Hero Patterns

Use for:

* Subtle backgrounds
* Repeating SVG patterns
* Decorative sections

---

## Haikei

Use for:

* Organic shapes
* SVG backgrounds
* Blob shapes
* Waves
* Abstract compositions

Use sparingly.

---

## SVG Backgrounds

Use for:

* Decorative SVG backgrounds
* Gradients
* Patterns

---

# 7. CSS TOOLS

Useful categories:

```text
Grid generators
Flexbox tools
Gradient generators
Shadow generators
Clip-path generators
Pattern generators
```

Use tools to speed up implementation, not to replace design reasoning.

---

# 8. RESOURCE PRIORITY

When multiple resources solve the same problem:

```text
1. Existing project design system
2. Accessible production component
3. Simple native CSS/HTML
4. Established component library
5. Specialized animation library
6. Experimental effect
```

Prefer the simplest solution that meets the design requirement.

---

# 9. IMPORTANT RULE

Do not turn the project into a collection of copied components.

The final interface must have:

```text
One visual identity
One color system
One typography system
One spacing system
One interaction language
One animation language
```

References provide ingredients.

The design system determines how those ingredients are combined.

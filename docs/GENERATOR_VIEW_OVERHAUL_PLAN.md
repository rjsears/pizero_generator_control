# Generator Control Tab Overhaul Plan

## Overview

This document outlines the comprehensive redesign of the Generator Control tab (`GeneratorView.vue`) to match the polished, collapsible card design patterns used in the n8n_nginx management console. The goal is to create a more compact, visually appealing interface with consistent styling, animations, and collapsible sections.

---

## Design Patterns Reference

Based on the n8n_nginx repository (`refactor/frontend-optimization-v2` branch), we'll implement:

### 1. Collapsible Card Structure
```
┌─────────────────────────────────────────────────────────────────┐
│  [Icon]  Title                              [Badge] [Badge] [▼] │
│          Subtitle description                                   │
├─────────────────────────────────────────────────────────────────┤
│  (Expanded content with smooth transition)                      │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Card Header Components
- **Icon**: Round background with color matching section theme
- **Title**: Bold, primary text
- **Subtitle**: Secondary text description
- **Status Badge**: Shows current state (Active/Disabled/etc.)
- **Count Badge**: Shows item counts where applicable
- **Chevron**: Rotates 90° on expand

### 3. Color Scheme
| Section | Icon Background | Icon Color | Badge Color |
|---------|----------------|------------|-------------|
| Generator Status | Green | `text-green-500` | `bg-green-50` |
| Fuel Tracking | Orange | `text-orange-500` | `bg-orange-50` |
| Manual Override | Amber | `text-amber-500` | `bg-amber-50` |
| Run Time Limits | Blue | `text-blue-500` | `bg-blue-50` |
| Exercise Schedule | Cyan | `text-cyan-500` | `bg-cyan-50` |
| Generator Info | Purple | `text-purple-500` | `bg-purple-50` |

### 4. Animations
- **section-expand**: Smooth collapse/expand with opacity and max-height
- **Chevron rotation**: 90° rotation on expand
- **Hover states**: Subtle background change on hover

---

## Current Layout vs. New Layout

### Current Layout (Vertical Stack)
```
[Control Row: GenSlave | Relay | Generator | Emergency Stop]  <- 4 boxes
[Generator Status Card]  [Victron Status Card]
[Fuel Usage Tracking Card - Full Width]
[Manual Override Card - Full Width]
[Run Time Limits Card - Full Width, Always Expanded]
[Statistics Row: Total Runs | Total Runtime | Avg Duration]
[Generator Information Card - Full Width, Always Expanded]
[Exercise Schedule Card - Full Width, Always Expanded]
```

### New Layout (Compact, Collapsible)
```
[Control Row: GenSlave | Relay | Emergency Stop]  <- 3 boxes (Generator toggle REMOVED)
[Generator Status Card]  [Victron Status Card]
[Fuel Usage Tracking]    [Manual Override]      <- Same row, compact
[Run Time Limits - Collapsible]                 <- Collapsed by default
[Statistics Row: Total Runs | Total Runtime | Avg Duration]
[Generator Information - Collapsible]           <- Collapsed by default
[Exercise Schedule - Collapsible]               <- Collapsed by default
```

> **Note**: The Generator toggle slider is removed from the top control row because the Generator Status card below already has Start/Stop buttons. Having both is redundant.

---

## Detailed Changes

### 1. Fuel Usage Tracking & Manual Override (Side by Side)

**Current**: Two separate full-width cards
**New**: Two cards on the same row (50/50 split on desktop, stacked on mobile)

#### Fuel Usage Tracking Card
- **Icon**: `FireIcon` with `bg-orange-50 dark:bg-orange-500/10`
- **Title**: "Fuel Usage"
- **Subtitle**: "Track fuel consumption"
- **Content**: Total gallons, reset date, reset button
- **No collapse**: Always visible (compact info)

#### Manual Override Card
- **Icon**: `HandRaisedIcon` with `bg-amber-50 dark:bg-amber-500/10`
- **Title**: "Manual Override"
- **Subtitle**: "Override Victron control"
- **Status Badge**: "Active" (green) or "Disabled" (gray)
- **Content**: Toggle switch, description
- **No collapse**: Always visible (simple toggle)

---

### 2. Run Time Limits (Collapsible)

**Current**: Always expanded, takes up significant vertical space
**New**: Collapsible card, collapsed by default

#### Header
- **Icon**: `ClockIcon` with `bg-blue-50 dark:bg-blue-500/10`
- **Title**: "Run Time Limits"
- **Subtitle**: "Configure automatic shutdown"
- **Status Badge**: "Enabled" (green) or "Disabled" (gray)
- **Chevron**: Rotates on expand

#### Expanded Content
- Enable/disable toggle
- Min/Max run time inputs
- Action selection (Manual Reset / Cooldown)
- Cooldown duration inputs
- Save button

---

### 3. Generator Information (Collapsible)

**Current**: `GeneratorInfoCard.vue` component, always expanded
**New**: Integrated collapsible card in GeneratorView

#### Header
- **Icon**: `InformationCircleIcon` with `bg-purple-50 dark:bg-purple-500/10`
- **Title**: "Generator Information"
- **Subtitle**: "Model, fuel capacity, and specifications"
- **Info Badge**: Shows model name if configured
- **Chevron**: Rotates on expand

#### Expanded Content
- Existing GeneratorInfoCard content
- Model, manufacturer details
- Fuel capacity and consumption rates
- Expected load settings

---

### 4. Exercise Schedule (Collapsible)

**Current**: `ExerciseScheduleCard.vue` component, always expanded
**New**: Integrated collapsible card in GeneratorView

#### Header
- **Icon**: `CalendarDaysIcon` with `bg-cyan-50 dark:bg-cyan-500/10`
- **Title**: "Exercise Schedule"
- **Subtitle**: "Automatic weekly exercise runs"
- **Status Badge**: "Enabled" (green) or "Disabled" (gray)
- **Next Run Badge**: Shows next scheduled time
- **Chevron**: Rotates on expand

#### Expanded Content
- Existing ExerciseScheduleCard content
- Enable toggle, day/time selection
- Duration and last run info

---

## Implementation Todo List

### Phase 1: Setup & Infrastructure
- [ ] Create feature branch `gencontrol_tab_overhaul`
- [ ] Remove Generator toggle from top control row (redundant with Start/Stop buttons)
- [ ] Update control row grid from 4 columns to 3 columns
- [ ] Add CSS transition classes for `section-expand` animation
- [ ] Add collapsible state refs (`runtimeLimitsExpanded`, `generatorInfoExpanded`, `exerciseScheduleExpanded`)
- [ ] Add toggle functions for each collapsible section

### Phase 2: Fuel Usage & Manual Override Row
- [ ] Create side-by-side layout with responsive grid
- [ ] Redesign Fuel Usage card with icon and colored styling
- [ ] Redesign Manual Override card with icon and status badge
- [ ] Add hover effects and transitions

### Phase 3: Run Time Limits Collapsible
- [ ] Convert to collapsible card structure
- [ ] Add colored header with icon, title, subtitle
- [ ] Add status badge (Enabled/Disabled)
- [ ] Add chevron with rotation animation
- [ ] Wrap content in Transition component
- [ ] Set collapsed as default state

### Phase 4: Generator Information Collapsible
- [ ] Inline GeneratorInfoCard content into GeneratorView
- [ ] Convert to collapsible card structure
- [ ] Add colored header with icon, title, subtitle
- [ ] Add info badge showing model name
- [ ] Add chevron with rotation animation
- [ ] Wrap content in Transition component
- [ ] Remove separate GeneratorInfoCard.vue import

### Phase 5: Exercise Schedule Collapsible
- [ ] Inline ExerciseScheduleCard content into GeneratorView
- [ ] Convert to collapsible card structure
- [ ] Add colored header with icon, title, subtitle
- [ ] Add status badge (Enabled/Disabled)
- [ ] Add "Next Run" badge showing next scheduled time
- [ ] Add chevron with rotation animation
- [ ] Wrap content in Transition component
- [ ] Remove separate ExerciseScheduleCard.vue import

### Phase 6: Polish & Testing
- [ ] Verify all animations work smoothly
- [ ] Test responsive behavior (mobile, tablet, desktop)
- [ ] Ensure dark mode styling is consistent
- [ ] Test all functionality still works after UI changes
- [ ] Review and adjust spacing/padding for consistency

### Phase 7: Cleanup
- [ ] Remove unused component imports if components are inlined
- [ ] Clean up any unused CSS
- [ ] Commit and push changes
- [ ] Create PR for review

---

## CSS Animations to Add

```css
/* Section expand/collapse transitions */
.section-expand-enter-active,
.section-expand-leave-active {
  transition: all 0.3s ease-out;
  overflow: hidden;
}

.section-expand-enter-from,
.section-expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.section-expand-enter-to,
.section-expand-leave-from {
  opacity: 1;
  max-height: 2000px;
}
```

---

## New Icons Required

| Icon | Section | Import From |
|------|---------|-------------|
| `FireIcon` | Fuel Usage | `@heroicons/vue/24/outline` |
| `HandRaisedIcon` | Manual Override | `@heroicons/vue/24/outline` |
| `ClockIcon` | Run Time Limits | Already imported |
| `InformationCircleIcon` | Generator Info | `@heroicons/vue/24/outline` |
| `CalendarDaysIcon` | Exercise Schedule | `@heroicons/vue/24/outline` |
| `ChevronRightIcon` | All collapsibles | `@heroicons/vue/24/outline` |

---

## Estimated Scope

- **Files Modified**: 1 (`GeneratorView.vue`)
- **Files Potentially Removed**: 2 (`GeneratorInfoCard.vue`, `ExerciseScheduleCard.vue`) - if fully inlined
- **New Components**: 0 (all changes in existing view)
- **CSS Changes**: Add transition animations

---

## Visual Mockup (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Generator Control                                                           │
│ Monitor and control the generator                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐                      │
│ │   GenSlave    │ │     Relay     │ │   Emergency   │   <- Control Row     │
│ │    Online     │ │     Armed     │ │     Stop      │      (3 boxes)       │
│ └───────────────┘ └───────────────┘ └───────────────┘                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────┐ ┌─────────────────────────────┐            │
│ │ [⚡] Generator Status       │ │ [📡] Victron Command        │            │
│ │     Running                 │ │     Generator Run           │            │
│ │     ██████████░░ 45m        │ │     GPIO17 HIGH             │            │
│ │     ████░░░░░░░░ 1.2 gal    │ │                             │            │
│ │     [Start] [Stop]          │ │                             │            │
│ └─────────────────────────────┘ └─────────────────────────────┘            │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────┐ ┌─────────────────────────────┐            │
│ │ [🔥] Fuel Usage             │ │ [✋] Manual Override         │            │
│ │     Track consumption       │ │     Override Victron     [○]│  <- Row    │
│ │     12.45 gal  [Reset]      │ │     [Disabled]              │            │
│ └─────────────────────────────┘ └─────────────────────────────┘            │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────────────────────────────────────┐  │
│ │ [🕐] Run Time Limits              [Enabled]                       [▶] │  │
│ │     Configure automatic shutdown                                      │  │
│ └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐                                     │
│ │Total Runs│ │ Runtime  │ │Avg Durat │   <- Statistics Row                 │
│ │    12    │ │  24h 30m │ │   2h 5m  │                                     │
│ └──────────┘ └──────────┘ └──────────┘                                     │
│                                                                             │
│ ┌───────────────────────────────────────────────────────────────────────┐  │
│ │ [ℹ️] Generator Information        [Generac GP3600]                [▶] │  │
│ │     Model, fuel capacity, and specifications                          │  │
│ └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│ ┌───────────────────────────────────────────────────────────────────────┐  │
│ │ [📅] Exercise Schedule            [Enabled] [Sun 10:00 AM]        [▶] │  │
│ │     Automatic weekly exercise runs                                    │  │
│ └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Approval

Once this plan is approved, implementation will begin following the todo list phases above.

**Branch**: `gencontrol_tab_overhaul`
**Target**: Merge to `main` via PR after testing

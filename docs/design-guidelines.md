# UI engineering decisions and skill-review record

Requested source: https://github.com/emilkowalski/skills

## Installation status

The requested command `npx --yes skills@latest add emilkowalski/skills` was attempted twice from the project environment:
- Attempt 1: timed out after 120 seconds.
- Attempt 2: timed out after 240 seconds.

The environment also failed to resolve the npm registry during package installation. The skill collection is therefore **not installed locally**. No local skill installation is claimed.

To continue applying the intended guidance, the public repository README and the relevant public skill documents were reviewed through GitHub:
- `emil-design-eng`
- `pick-ui-library`
- `apple-design`
- `remove-animations`
- `animation-performance`
- `mobile-native`
- `break-ui`

## Applied guidance

- Use a restrained visual hierarchy, neutral surfaces, consistent spacing, accessible controls and readable typography.
- Avoid decorative animation. Use only short, direct hover/press feedback; respect `prefers-reduced-motion`.
- Keep the main interaction path responsive; do not add loading delays or page-transition animation.
- Prefer CSS and native browser behavior over adding a large animation dependency.
- Use mobile-aware viewport sizing, safe-area padding, touch-target feedback and 16px form controls on coarse pointers.
- Keep wide tables horizontally scrollable on narrow screens.
- Use explicit loading, empty, error and success states.
- Keep the interface data-driven: business records are loaded from the API, not hardcoded into the dashboard.

## Not yet verified

- The `break-ui` stress cases have not been exercised in a browser with real worst-case fixture data.
- Mobile behaviour has not been tested on physical iOS/Android hardware.
- Motion performance has not been profiled on a mid-range phone.
- Since the skill package could not be installed, this is a documented manual review of public instructions, not an installed-skill execution.


## Motion review

- No `transition: all`; transition only the properties that visibly change.
- Press feedback is subtle (`scale(.98)`), with a 160 ms press and a faster 100 ms return.
- Hover behavior is gated to fine pointers; coarse-pointer devices do not depend on hover.
- Reduced-motion mode removes button movement while preserving useful color/opacity feedback rather than globally setting every transition to zero.
- Avoid layout-property animation; use transform/opacity only when movement is justified.
- The dashboard favors restrained, occasional transitions over entrance choreography or persistent decorative motion.

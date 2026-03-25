# Why

## What this library does

D3's API is well-documented. What's not documented is the thousand small decisions that separate a chart that communicates from one that merely renders: where the tick falls, how much whitespace to leave, when to use color and when to use position, why this projection and not that one.

These decisions live in practitioners as taste — pattern recognition trained on failure. You learn where the tick should fall by putting it in the wrong place a hundred times. The knowledge is real but it's trapped in muscle memory and aesthetic discomfort.

This library extracts that knowledge into structured context that both humans and models can use. Each skill encodes the judgment calls behind a specific visualization type, so you get a floor of quality without rediscovering every pitfall.

## Rules and rationales

Every skill is an approximation. There is always a gap between the rule and the judgment that produced it.

The rule says: "use `scaleSqrt` for bubble area so perceived size scales linearly with value." The judgment behind it is subtler — you've seen the chart where someone used a linear scale and the big bubbles dominated everything. You remember the meeting where someone misread the data because of it. The rule encodes the *what*. The experience encodes the *why it matters*.

We close this gap by writing rationales alongside rules. Each skill explains the geometry, the perception, the failure mode. A rule without a rationale is a rule someone will break for the wrong reasons.

## Interaction over rendering

Rendering is translation — data to pixels. Interaction is conversation — human and data.

When you drag a brush across a parallel coordinates axis, you're constraining the dataset: *show me only the rows where this variable falls in this range*. The data answers by revealing structure. Lines bundle. Correlations appear. A relationship between dimensions that was invisible in the static view becomes obvious.

A static chart is a statement. A brushable chart is a question the viewer can ask. The skills in this library treat interaction as first-class — not an enhancement bolted on after rendering works, but the reason the chart exists.

## Composition

This library includes skills that compose other skills — meta-skills for linking views, layering Canvas and SVG, managing shared state. Composition is a legitimate domain with its own judgment calls.

But abstraction for its own sake adds complexity without helping anyone see their data. Every layer of composition should eventually produce a chart someone looks at and understands. If it doesn't, it's architecture for no one.

## Opinionated but bendable

Skills should be opinionated enough to prevent bad defaults but open enough to be bent. The floor, not the ceiling. Strong conventions, light constraints.

The deepest success is when someone uses a skill to build something the skill's author wouldn't have built — and it works.

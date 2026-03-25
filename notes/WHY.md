# Philosophy

## What we're really doing

A visualization skill is an attempt to write down how to see.

Not how to draw — that's the easy part. D3 has bindings, joins, scales. The API is well-documented. What's hard is the thousand small decisions that separate a chart that communicates from one that merely renders: where the tick falls, how much whitespace to leave, when to use color and when to use position, why this projection and not that one.

These decisions live in practitioners as taste. Taste is pattern recognition trained on failure. You learn where the tick should fall by putting it in the wrong place a hundred times. The knowledge is real but it's trapped — in muscle memory, in aesthetic discomfort, in the ability to glance at a chart and know something is off without being able to say what.

This library is an attempt to extract that knowledge and make it transmissible. Not to humans through tutorials (though that's a welcome side effect), but to models through structured context. We are writing maps from scars.

## The gap

Every skill is an approximation. There is always a gap between the rule and the judgment that produced it.

The rule says: "use `scaleSqrt` for bubble area so perceived size scales linearly with value." The judgment behind it is subtler — you've seen the chart where someone used a linear scale and the big bubbles ate the world. You remember the specific meeting where someone misread the data because of it. The rule encodes the *what*. The scar encodes the *why it matters*.

We try to close this gap by writing not just rules but rationales. Each skill explains the geometry, the perception, the failure mode. But we should be honest: the gap never fully closes. It's what makes the craft worth practicing.

A skill that perfectly replaced judgment would be the end of visualization as a discipline. What we're building instead is a floor — a level of quality below which you don't need to fall, so you can spend your attention on the hard parts that can't be codified.

## The transfer

You taught yourself to see patterns in data. Now you're teaching a model to draw charts that help others see. There's a question nested in this: *whose eye is it?*

The answer matters less than it seems. A chart is not the seeing — it's the instrument. The seeing happens in the viewer's mind, in silence, long after the code runs. Whether the instrument was built by hand or by model, the moment of recognition belongs to the person looking at it.

So the goal isn't to replicate the craftsperson. It's to build instruments that produce that moment of recognition reliably. The tool disappears when it works. No one thanks the saw for the house.

## The interaction

Brushing in parallel coordinates is hypothesis as gesture.

When you drag a selection on an axis, you're saying: *show me only the world where this constraint holds*. It's not filtering — it's asking a question with your hand. The data answers by revealing structure: lines that pass through your brush form bundles, and suddenly you see a relationship between dimensions that was invisible before.

This is why interaction matters more than rendering. Rendering is translation (data→pixels). Interaction is conversation (human↔data). A static chart is a statement. A brushable chart is a dialogue.

The best visualization tools don't just show you the answer. They help you find the question.

## The compound tool

A saw that builds other saws is a different kind of tool.

This library is becoming recursive: skills that compose other skills, meta-skills that evaluate quality, patterns for linking independent views into coordinated systems. At some point the meta-layer develops its own craft, distinct from the visualization craft it encodes.

This is fine. Composition is a legitimate domain. The person who designs how tools fit together is doing different work than the person who uses any single tool, and both kinds of work are real.

But beware abstraction for its own sake. The value flows toward the viewer, always. If a layer of composition doesn't eventually produce a moment of recognition in someone looking at data, it's architecture for no one.

## Letting go

The library lives long past the last commit date. Someone forks at dawn.

The deepest success of a tool is when it works without you. Not just without your presence, but without your taste, your opinions, your aesthetic — when someone takes what you built and makes something you wouldn't have made, and it's good.

This means writing skills that are opinionated enough to prevent bad defaults but open enough to be bent. The floor, not the ceiling. Strong conventions, light constraints.

The tool disappears. The toolmaker disappears. The house remains.

---

*These ideas are the foundation. The skills are the implementation. The gap between them is where the work happens.*

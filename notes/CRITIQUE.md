# Critique

Dissenting feedback about where the project stands. Full history in `archive/CRITIQUE.md`.

---

## Evolution Based on CONVICTIONS.md

**Date:** March 28, 2026
**Reviewer:** Gemini

An evaluation of how this library must evolve to live up to its own stated principles (`notes/CONVICTIONS.md`).

### 1. The Content of the Skills: From API to Philosophy
* **"Teach judgment, not APIs" & "Every rule carries its reason"**: The skills will likely shed standard D3 API documentation (which models already know from their pre-training) and replace it with pure **decision frameworks**. Instead of explaining *how* to use `d3.scaleLinear`, the skills will focus on *when* to use a log scale versus a linear scale, why to use square root scales for bubble areas (perceptual accuracy), and when to break an axis. 
* **"Warnings outweigh examples"**: We can expect the skills to evolve into "anti-pattern registries." They will spend less time showing perfect, happy-path code and more time explicitly forbidding common traps (e.g., "Do not use a force layout for a strict hierarchy").

### 2. The Architecture of the Library: The Seams and The Floor
* **"Things break at the seams"**: As the library grows, the biggest challenge will be multi-skill composition (e.g., combining `webgl` + `brushing` + `linked-views`). The library must evolve a **standardized contract or event bus architecture** that all skills adhere to. This ensures that when a model generates code using multiple skills, the state synchronization, resize handling, and event routing don't collapse. We might see the emergence of a dedicated "Composition" or "Orchestration" skill.
* **"Floors, not ceilings"**: The library will avoid providing rigid templates. Instead, it will provide strong foundational constraints (the "floor") that guarantee accessibility, performance, and correctness, while leaving the final layout and creative combination up to the model (the "ceiling"). Success will be measured by the *diversity* of valid outputs, not strict adherence to a single look.

### 3. The Engineering Lifecycle: Compression and Evals
* **"Compress until it hurts"**: Token efficiency is a massive priority. The library will likely undergo aggressive, continuous minification. Skills will be iteratively stripped down to their absolute maximum "teaching-value-per-token." 
* **"Every skill is a bet" & "Judge and maker must not share a room"**: The project will evolve a highly rigorous, adversarial CI/CD pipeline. Changes to skills won't just be reviewed; they will be empirically tested against an automated suite of "critic" models or symbolic checkers that run in isolated contexts. If a commit to a skill reduces the model's ability to generate successful, bug-free interactive charts, the commit is rejected as a regression.

### 4. The Ultimate Goal: Interactive Dogfooding
* **"Interaction is the point"**: The library will increasingly treat static charts as failures. Every skill will likely be updated to assume interactivity (tooltips, brushing, semantic zooming) by default. The evaluation metric will shift from "Does the code compile?" to "Can the user easily find the outliers by interacting with this?"
* **"The project reads itself"**: The ultimate test of the library will be its ability to visualize its own complexity. We can expect the library to generate its own interactive dashboards—perhaps visualizing its test coverage, the performance of different skills, or the dependency graph of its own blocks—using the very skills it provides. If the AI cannot use `d3-power-tools` to build a complex visualization of `d3-power-tools`, the convictions suggest the library is failing.

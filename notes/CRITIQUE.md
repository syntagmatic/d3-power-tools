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

---

## Plan Evaluation: Simplification & Infrastructure

**Date:** March 29, 2026
**Reviewer:** Gemini

The proposed plan in `notes/IDEAS.md`, supported by the `CONVICTIONS.md` and `CRITIQUE.md`, is a sophisticated roadmap for evolving the library from a collection of "D3 templates" into a high-leverage "judgment engine" for AI-assisted visualization.

### **Executive Summary of the Plan**
The plan focuses on two primary axes: **Simplification** (reducing token overhead and redundancy) and **Infrastructure** (implementing rigorous, adversarial validation).

1.  **Simplification:**
    *   **Prompt Compression:** Reducing the 160-word prompts for blocks 01–84 to 30–60 words, shifting implementation responsibility to the skills.
    *   **Skill Distillation:** Stripping API documentation from the largest skills (e.g., `cartography`, `webgl`) to focus on decision frameworks, targeting <300 lines each.
    *   **Structural Consolidation:** Merging 11 meta-skills into 6 and culling redundant examples.
2.  **Infrastructure:**
    *   **Eval as CI:** Automated scoring of skill effectiveness on every commit.
    *   **Asymmetric Evaluation:** Using different models or symbolic checkers to judge output, avoiding "shared-bias" errors.

### **Evaluation & Strategic Critique**

#### **1. The "Judgment over API" Pivot (High Impact)**
The most valuable part of this plan is the shift away from teaching D3 syntax (which models already know) toward teaching **visualization taste**.
*   **Strength:** This leverages the unique value of the library. It transforms a skill from a "cheat sheet" into a "perceptual guardrail."
*   **Risk:** There is a "compression floor." If you remove too much implementation detail, the model may revert to its mediocre pre-trained defaults.
*   **Recommendation:** When compressing, ensure each "judgment" is still paired with a concise **code-idiom** (e.g., instead of documenting `d3.scaleSqrt`, keep the idiom `const r = d3.scaleSqrt().range([0, maxR])` for bubbles).

#### **2. The "Seams" Problem (Architectural Gap)**
`CRITIQUE.md` correctly identifies that "things break at the seams" (interaction between skills).
*   **Observation:** The current plan to consolidate meta-skills is good, but the "Composition" skill needs to be more than just documentation. 
*   **Recommendation:** The plan should prioritize a **Standard Interaction Contract** (e.g., a shared `d3.dispatch` namespace or a specific `state` object pattern) that all skills are instructed to use. This makes multi-skill blocks (like `webgl` + `brushing`) deterministic.

#### **3. Infrastructure and Asymmetric Eval (Sophisticated but Heavy)**
The "Eval as CI" and "Asymmetric evaluation" are industry-leading approaches for AI-tool development.
*   **Strength:** It moves the project from subjective quality to empirical "bets."
*   **Risk:** High maintenance. Symbolic checkers for "visual logic" are difficult to write.
*   **Recommendation:** Start with **"Metamorphic Testing"** (e.g., if I change the data, does the chart update accordingly?) as a simpler form of automated evaluation before moving to full model-based grading.

### **Recommended Prioritization**

1.  **Immediate (Low Effort, High Cleanup):**
    *   Consolidate meta-skills (11 → 6).
    *   Delete `notes/archive/`.
2.  **Short-term (Validation of the "Compress" Bet):**
    *   Rewrite prompts for Blocks 01–10. Regenerate them and compare to the original versions. If quality holds, proceed with the rest.
3.  **Medium-term (Core Value):**
    *   Distill the Top 6 skills. Focus on adding "Anti-pattern registries" (what NOT to do) which provide more signal-per-token than happy-path examples.
4.  **Long-term (Infrastructure):**
    *   Wire the "Eval as CI" pipeline.

**Verdict:** The plan is sound, highly principled, and correctly identifies token efficiency as the primary constraint for AI tool usage in 2026. **I recommend proceeding with the Consolidation and the Prompt Compression pilot (01-10) immediately.**

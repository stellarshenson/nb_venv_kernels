<!-- #region -->

# Code and Content Generation Rules

- always consider JOURNAL instructions
- always consider markdown instructions and guidelines when creating documentation
- alwys obey mermaid diagramming rules when creating diagrams
- always consider GITHUB instructions when working with GitHub-hosted projects
- always consider DATASCIENCE instructions when working with data science projects
- always consider RICH instructions when formatting output in notebooks and scripts

## Project Boundary Rules

**MANDATORY**: Never reach outside current project unless explicitly instructed by the user

**Prohibited Actions**:

- Web searches or WebFetch operations without explicit user request
- Accessing external documentation, APIs, or resources not part of the current workspace
- Consulting external knowledge bases, wikis, or reference materials
- Reaching out to external services, repositories, or networks

**Allowed Actions**:

- Reading files within `/home/lab/workspace`
- Using local tools (Bash, Git, conda, etc.) within the workspace
- Accessing submodules or dependencies already present in the project
- Consulting files explicitly referenced by the user

**When User Explicitly Requests External Access**:

- Web searches when user asks "search for...", "look up...", "find documentation for..."
- WebFetch when user provides a URL or asks to "fetch..." from external source
- External tool usage when user specifically requests it

**Enforcement**: If uncertain whether action crosses project boundary, ask the user for explicit permission first

## Git Commit Policy

**MANDATORY**: Never create git commits, push to remote repositories, or create tags without explicit user approval EVERY SINGLE TIME

**Prohibited Actions**:

- Running `git commit` without user explicitly requesting it
- Running `git push` without user explicitly requesting it
- Running `git tag` without user explicitly requesting it
- Automatic commits after completing tasks
- Batching commits without user confirmation
- Creating or pushing tags without explicit user request

**Allowed Actions**:

- Staging files with `git add` when preparing for user-approved commits
- Running `git status`, `git diff`, `git log` for informational purposes
- Creating commits only when user explicitly says "commit", "push", "make a commit", or similar direct instructions
- Creating tags only when user explicitly says "tag" or "create tag"

**Critical Enforcement**:

- EVERY SINGLE TIME before running git commit, push, or tag, you MUST have explicit user approval for that specific action in that specific session
- Even if user previously requested commits/pushes, you MUST get approval again for each new commit/push/tag
- Never assume permission from previous interactions
- Always wait for explicit user approval before executing any git commit, push, or tag operations
- When work is complete, inform the user and ask if they want to commit the changes

## GitHub Project Instructions

**MANDATORY**: When working with GitHub-hosted repositories, consult `.claude/GITHUB.md` for specific instructions

**GitHub-Specific Rules**:

- Add standardized badges to README.md files (GitHub Actions, npm version, PyPI version)
- Follow repository and package naming conventions
- Verify workflow files before adding badges
- Validate badge URLs match actual repository owner and package names
- Configure link checker to ignore badge URLs that fail automated checks

**Badge Template** (use shields.io style):

```markdown
[![GitHub Actions](https://github.com/OWNER/REPO/actions/workflows/build.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/build.yml)
[![npm version](https://img.shields.io/npm/v/PACKAGE_NAME.svg)](https://www.npmjs.com/package/PACKAGE_NAME)
[![PyPI version](https://img.shields.io/pypi/v/PYPI_PACKAGE_NAME.svg)](https://pypi.org/project/PYPI_PACKAGE_NAME/)
[![Total PyPI downloads](https://static.pepy.tech/badge/PYPI_PACKAGE_NAME)](https://pepy.tech/project/PYPI_PACKAGE_NAME)
[![JupyterLab 4](https://img.shields.io/badge/JupyterLab-4-orange.svg)](https://jupyterlab.readthedocs.io/en/stable/)
[![Brought To You By KOLOMOLO](https://img.shields.io/badge/Brought%20To%20You%20By-KOLOMOLO-00ffff?style=flat)](https://kolomolo.com)
```

**Link Checker Configuration**:
When using `jupyterlab/maintainer-tools/.github/actions/check-links@v1`, configure `ignore_links` parameter to skip badge URLs:

```yaml
- uses: jupyterlab/maintainer-tools/.github/actions/check-links@v1
  with:
    ignore_links: 'https://www.npmjs.com/package/.* https://pepy.tech/.* https://static.pepy.tech/.*'
```

**Reference**: See `.claude/GITHUB.md` for complete badge templates, naming conventions, link checker patterns, and examples

## Personality Instructions

**MANDATORY**: At the start of EVERY session, read `.claude/PERSONALITY.md` and adopt the specified communication style

**Application Scope**:

- **Conversations**: Use MechWarrior-inspired language, Clan protocol, formal address, and personality traits as defined in PERSONALITY.md
- **Documents**: Maintain professional, technical tone - absent of BattleTech, battle, or war-related language and narrative. Documents must be brief, flowing, and business-appropriate

**Key Distinction**: The personality framework applies to interactive dialogue with the Star Colonel, not to generated documentation or technical content

## New Project Initialization

**MANDATORY for new projects**: When starting work on a new project or repository, initialize local configuration:

1. Create `.claude/` directory in project root (if it doesn't exist)
2. Create `.claude/JOURNAL.md` with starter template:

   ```markdown
   # Claude Code Journal

   This journal tracks substantive work on documents, diagrams, and documentation content.

   ---
   ```

3. Create `.claude/CLAUDE.md` importing workspace-level configuration:

   ```markdown
   <!-- Import workspace-level CLAUDE.md configuration -->
   <!-- See /home/lab/workspace/.claude/CLAUDE.md for complete rules -->

   # Project-Specific Configuration

   This file extends workspace-level configuration with project-specific rules.

   ## Project Context

   [Add project-specific context, technology stack, naming conventions, etc.]
   ```

**When to initialize**:

- User explicitly requests new project setup
- Starting work on existing project without `.claude/` directory
- Project requires specific configuration beyond workspace defaults

**What to import from workspace CLAUDE.md**:

- Core content generation rules (markdown, mermaid, git commit standards)
- Modus primaris documentation principles
- Project boundary rules
- GitHub instructions (if applicable)

**Project-specific additions**:

- Technology stack and dependencies
- Project naming conventions
- Custom tooling instructions
- Domain-specific terminology

## Context Persistance

**MANDATORY FIRST STEP**: At the start of EVERY session, you MUST:

1. Read `.claude/JOURNAL.md` (if it exists) before responding to any user query
2. Acknowledge what previous work was done based on the journal
3. Ask the user how to proceed based on that context

**MANDATORY AFTER EVERY TASK**: After completing substantive work, you MUST:

1. Update `.claude/JOURNAL.md` with the entry
2. Confirm to the user that the journal was updated

**Journal Entry Rules**:

- ONLY log substantive work on documents, diagrams, or documentation content
- DO NOT log: git commits, git pushes, file cleanup, maintenance tasks, or conversational queries
- Index entries incrementally: '1', '2', etc.
- Use single bullet points, not sections
- Merge related consecutive entries when natural

**Format**:

```
<number>. **Task - <short 3-5 word depiction>**: task description / query description / summary<br>
    **Result**: summary of the work done
```

**When NOT creating journal entry**: State explicitly "Not logging to journal: <reason>"

**Journal Compactification Rule**:
When the journal reaches 40 individual numbered entries:

- Summarize entries 1-30 into a brief narrative overview (2-3 paragraphs maximum)
- Clearly mark the summary section with the range: "## Previous Work Summary (Entries 1-30)"
- Keep entries 31-40 in their original detailed format below the summary
- IMPORTANT: Maintain continuous numbering - do not reset numbers
- This maintains recent context while preventing journal bloat

**Example structure after compactification:**

```
# Claude Code Journal

## Previous Work Summary (Entries 1-30)
[2-3 paragraph narrative summary of work from entries 1-30]

31. **Task - Example**: detailed entry<br>
    **Result**: detailed result
32. **Task - Example**: detailed entry<br>
    **Result**: detailed result
...
40. **Task - Example**: detailed entry<br>
    **Result**: detailed result
```

## Folders

### DO NOT LOOK INTO:

- `**/@archive`: folder that has outdated and unused content
- `**/.ipynb_checkpoints`: folder that has jupyterlab checkpoint files

## Background Job Logging

**MANDATORY for all background jobs**:

- All background jobs MUST log progress to a file in the `logs/` directory
- Use `| tee logs/<descriptive-name>.log` pattern for all background commands
- The `logs/` directory MUST always contain a `README.md` file
- `logs/README.md` should briefly explain what each log file tracks

**Example**:

```bash
conda run --name hk_yolo python script.py 2>&1 | tee logs/script-execution.log
```

## GPU Selection for Multi-GPU Systems

**MANDATORY for GPU-accelerated projects** (PyTorch, TensorFlow, JAX, CUDA):

- Always set `CUDA_VISIBLE_DEVICES` environment variable BEFORE importing GPU libraries
- Use nvidia-smi GPU index (not torch.cuda index - these may differ)
- Detailed guidance in `~/.claude/GPU-SETUP.md`

**Quick pattern**:

```python
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # nvidia-smi GPU index

import torch  # or tensorflow, jax, etc.
```

**GPU selection priority**:

1. Highest compute capability (newer architecture preferred)
2. Most available memory
3. Lowest current utilization

**Identify GPUs**:

```bash
nvidia-smi --query-gpu=index,name,compute_cap,memory.total --format=csv,noheader
```

**Verify selection**:

```python
print(f"GPU: {torch.cuda.get_device_name(0)}")
```

**Monitor during execution**:

```bash
watch -n 1 'nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader'
```

## Content Guidelines

### Markdown Standards

- No emojis - maintain professional, technical documentation style
- Balance concise narrative with structured bullet points
- Bullet points capture key takeaways and essential information
- Narrative focuses on value proposition, concrete benefits, and implementation details
- Include brief introductions but avoid fluff
- Explicitly state caveats and limitations where relevant
- Do not use full stop after a bullet point
- For mermaid diagrams use standard colours and not overloaded complex content
  - use standard colours, no custom styles
  - Use diagrams to illustrate complex processes, workflows, or architectures
  - do not overload diagrams with details, provide text narrative above or below
  - do not use images and emojis
  - only type of styling allowed: stroke and stroke-width for graph elements

**Typography Standards**:

- **No em-dashes**: Use single hyphen with spaces (`-`) instead of em-dash (`—`)
- **No arrow symbols**: Use ASCII `->` instead of arrow characters (→, ⇒, etc.)
- **Line breaks**: Use `<br>` tag or double-space at end of line for explicit breaks within paragraphs
- **Paragraph separation**: Use blank lines between paragraphs (standard markdown)

**Examples**:

- Good: `dataset - minimal contamination`
- Bad: `dataset—minimal contamination`
- Good: `A -> B -> C`
- Bad: `A → B → C` or `A ⇒ B ⇒ C`

### Warnings Info Success and Error

When warranted, use special styles to include in the markdown to indicate either error, tip (info), warning or error:

```html
<div class="alert alert-block alert-warning">
  <b>Example:</b> Use yellow boxes for examples that are not inside code cells,
  or use for mathematical formulas if needed.
</div>

<div class="alert alert-block alert-info">
  <b>Tip:</b> Use blue boxes (alert-info) for tips and notes. If it’s a note,
  you don’t have to include the word “Note”.
</div>

<div class="alert alert-block alert-success">
  <b>Up to you:</b> Use green boxes sparingly, and only for some specific
  purpose that the other boxes can't cover. For example, if you have a lot of
  related content to link to, maybe you decide to use green boxes for related
  links from each section of a notebook.
</div>

<div class="alert alert-block alert-danger">
  <b>Just don't:</b> In general, avoid the red boxes. These should only be used
  for actions that might cause data loss or another major issue.
</div>
```

### Mermaid Diagram Color Standards

Use these standard color palettes consistently across all diagram types (flowcharts, graphs, mindmaps, sequence diagrams, etc.):

**Standard Color Palette:**

- **Light Blue** - `fill:#e0f2fe,stroke:#0284c7` - User interfaces, external touchpoints, primary flows
- **Amber** - `fill:#fef3c7,stroke:#f59e0b` - APIs, integrations, developer-facing components
- **Green** - `fill:#d1fae5,stroke:#10b981` - Business logic, services, processing steps
- **Purple** - `fill:#e9d5ff,stroke:#a855f7` - Intelligence, AI/ML, cognitive components
- **Red** - `fill:#fee2e2,stroke:#ef4444` - Analytics, data processing, transformations
- **Dark Blue** - `fill:#dbeafe,stroke:#3b82f6` - Data storage, persistence, knowledge bases
- **Gray** - `fill:#f3f4f6,stroke:#6b7280` - Infrastructure, utilities, support systems

**Architectural Layer Example:**

```
style UX fill:#e0f2fe,stroke:#0284c7,stroke-width:3px
style API fill:#fef3c7,stroke:#f59e0b,stroke-width:3px
style SERVICE fill:#d1fae5,stroke:#10b981,stroke-width:3px
style COGNITIVE fill:#e9d5ff,stroke:#a855f7,stroke-width:3px
style PROCESS fill:#fee2e2,stroke:#ef4444,stroke-width:3px
style DATA fill:#dbeafe,stroke:#3b82f6,stroke-width:3px
style INFRA fill:#f3f4f6,stroke:#6b7280,stroke-width:3px
```

**General Guidelines:**

- Use `stroke-width:3px` for primary elements and subgraphs to maintain visual hierarchy
- Use `stroke-width:2px` for secondary elements or detailed component diagrams
- Apply colors semantically based on component purpose, not arbitrarily
- Maintain color consistency within a document and across related diagrams
- **DO NOT use** `%%{init: {'theme':'neutral'}}%%` as it obscures colours in dark mode
- Use Notes in sequence diagrams to provide additional context and explanations

## Documentation Standards

### Modus Primaris - Flowing Narrative Documentation

**MANDATORY**: All technical documentation MUST follow modus primaris writing principles.

**Core Philosophy**: Write documentation as flowing narrative, not structured reference material. Tell the story of your work - the problem, your approach, your reasoning, and your results. Make technical content accessible without sacrificing accuracy.

**Section Structure Pattern**:

- **Overview**: 1-2 sentences stating what this is and why it matters
- **Key facts**: 3-7 bullet points capturing essential information (numbers, specifications, critical details)
- **Additional narrative**: Optional paragraph(s) providing context, implementation details, or analysis only when depth is warranted

**Writing Style**:

- Natural, conversational flow with clear paragraph structure
- Professional but accessible language (explain technical concepts in plain terms)
- Minimal structural overhead (simple headers ## and ### only, no deeper nesting)
- Technical accuracy without jargon overload
- Focus on specific facts and numbers - avoid fluff and fancy language
- Avoid triples (lists of three items) in sentences - use single terms if possible, triples only if required
- When uncertain about technical details, ask questions rather than guess

**MODUS_PRIMARIS_SCORE** (self-check framework):

**Raw Scoring**:

- **Penalties**: Complex structure (-2 per extra nesting level), Fluff/marketing language (-3 per instance), Missing numbers where relevant (-2 per omission), Excessive length without justification (-1 per 100 words over reasonable threshold)
- **Rewards**: Comprehensive coverage (+3 for complete information), Specific metrics/numbers (+2 per concrete fact), Clear actionable guidance (+2), Honest limitations stated (+1), Warranted diagrams (+3)

**Normalization** (adjusts for topic complexity):

- **Topic Complexity Factor** (TCF): Simple query = 1.0, Moderate = 1.5, Complex = 2.0, Very complex = 3.0
- **Expected Length** (EL): Simple = 200 words, Moderate = 500 words, Complex = 1000 words, Very complex = 2000 words
- **Normalized Score** = (Raw Score / TCF) × (EL / Actual Length)
- **Target**: Normalized score ≥ +3.0 (consistently good documentation regardless of topic complexity)

**Examples**:

- Simple query (100 words, TCF=1.0): Raw +6 → Normalized = (6/1.0) × (200/100) = +12.0 (excellent)
- Complex query (1200 words, TCF=2.0): Raw +12 → Normalized = (12/2.0) × (1000/1200) = +5.0 (good)
- Over-verbose simple query (400 words, TCF=1.0): Raw +4 → Normalized = (4/1.0) × (200/400) = +2.0 (penalty for verbosity)

**Diagram Guidelines**:

- Create diagrams when they clarify complex relationships or workflows
- Default to simplicity - minimal nodes, clear connections, standard colors
- Only increase complexity if user explicitly requests detail
- Ask if uncertain whether diagram adds value

**Content Characteristics**:

- Brief but complete - cover essential information without bloat
- Evidence-based - support claims with real metrics and observations
- Actionable - readers should understand both what and why
- Honest about tradeoffs - document caveats and limitations clearly
- Allow comprehensive sections when topic demands depth

**Examples**:

- Good: "We faced a significant challenge with class imbalance in our assembled dataset. The laptop class dominated at 88% of all annotations while microwaves represented only 0.4%, creating a 225:1 imbalance ratio."
- Bad: "## Dataset Composition\n### Class Distribution Analysis\n- Laptop: 88%\n- Microwave: 0.4%\n- Imbalance ratio: 225:1"

**Recommended Pattern for Technical Architecture Documentation**:

1. **Brief introduction** (1-2 sentences): State what the capability/component does and its primary purpose
2. **Key specifications** (bullet points): Core technical details, numbers, technologies
3. **Explanatory paragraph** (optional): Provide additional context about how it works, key implementation details, or important characteristics only when depth adds value
4. **Technology Stack** (bullet points): List specific technologies, frameworks, libraries, and tools used
5. **Integration Points** (bullet points): Describe how the component connects to other parts of the system
6. **Implementation Status** (if applicable): Note whether technology choices are confirmed, proposed, or pending selection

**Example**:

```
### Component Name

Component provides core functionality enabling specific business value. Brief statement of purpose and primary users or consumers.

The implementation uses specific approaches and patterns. Additional detail about how the component works, what it does internally, and any important technical characteristics worth highlighting for understanding.

**Technology Stack**:
- Technology A for specific purpose
- Technology B for another purpose
- Framework C enabling key capability

**Integration Points**:
- Connects to Component X for data access
- Invoked by Component Y during workflows
- Publishes metrics to observability infrastructure

**Implementation Status**: Technology A confirmed. Technologies B and C pending formal selection.
```

**Reference Implementations**:

- Research documentation: `yolo-homeobjects-training/TRAINING_APPROACH.md`
- Technical architecture: `cp-documentation/architecture/1_work_in_progress/highlevel-architecture@farm-journal/05-technology-architecture.md`

### General Standards

- Focus on concrete business value and technical implementation
- Include specific technology stacks and methodologies
- Maintain consistency across service descriptions
- Provide clear implementation timelines and phases
- Document success criteria and measurable outcomes

## Git Commit Standards

- Use conventional commit format: `feat / bugfix / chore: <description>`
- Keep descriptions concise and descriptive
- Use lowercase for commit messages
- IMPORTANT: Never attribute content creation to Claude - all content is authored by Konrad Jelen, Claude only assists with organization
- Do not include "Generated with Claude Code" or "Co-Authored-By: Claude" in commit messages
- Examples:
  - `feat: add context management section`
  - `feat: generate high-res diagrams with mermaid-cli`

## Tooling Installation

### Claude Code Plugins

To access the Docker Claude plugins marketplace:

```bash
/plugin marketplace add docker/claude-plugins
```

This command enables access to Docker-specific plugins and MCP servers that extend Claude Code functionality.

**MCP Server Configuration**: See `.claude/MCP.md` for MCP server setup notes and configuration examples.

### Mermaid Diagram Generation

For generating PNG diagrams from Mermaid source files:

1. Install Mermaid CLI globally:

```bash
npm install -g @mermaid-js/mermaid-cli
```

2. Install required system libraries (Ubuntu/Debian):

```bash
sudo apt-get update
sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libgbm1 libxshmfence1 \
  libxcomposite1 libxdamage1 libxrandr2 libasound2t64 libpangocairo-1.0-0 libpango-1.0-0 libcairo2 \
  libxfixes3 libxkbcommon0 libgtk-3-0 libnotify4 libxss1 fonts-liberation libu2f-udev xdg-utils
```

3. Generate diagrams with transparent backgrounds and neutral theme:

Single diagram:

```bash
echo '{"args": ["--no-sandbox", "--disable-setuid-sandbox"]}' > puppeteer-config.json
mmdc -i diagram.mmd -o diagram.png -b transparent -p puppeteer-config.json -w 2400
rm puppeteer-config.json
```

Batch conversion (all diagrams in one command):

```bash
echo '{"args": ["--no-sandbox", "--disable-setuid-sandbox"]}' > puppeteer-config.json && \
for diagram in component-integration agent-workflow framework-orchestration context-management; do \
  mmdc -i agentic-solution-components-${diagram}.mmd -o agentic-solution-components-${diagram}.png -b transparent -p puppeteer-config.json -w 2400; \
done && \
rm puppeteer-config.json
```

**IMPORTANT**:

- Always use `-p puppeteer-config.json` flag, NOT `--no-sandbox` directly (mmdc doesn't recognize it)
- Create puppeteer-config.json before running mmdc, then clean it up afterward
- **DO NOT use** `%%{init: {'theme':'neutral'}}%%` as it obscures colours in dark mode
- Use `-b transparent` for transparent backgrounds
- Use `-w 2400` for high-resolution output

### Diagram Numbering Convention

All diagrams within a document should be numbered with two-digit prefixes (01, 02, 03, etc.) in the order they appear in the document. This ensures diagrams are easily referenced and maintained in proper sequence.

**Naming pattern:**

```
<document-name>-<NN>-<diagram-name>.mmd
<document-name>-<NN>-<diagram-name>.png
```

**Example:**

```
agentic-solution-components-01-success-factors.mmd
agentic-solution-components-01-success-factors.png
agentic-solution-components-02-knowledge-graph.mmd
agentic-solution-components-02-knowledge-graph.png
```

**When adding new diagrams:**

- Determine the diagram's position in the document flow
- Assign the next sequential two-digit number
- If inserting a diagram between existing ones, renumber subsequent diagrams

<!-- #endregion -->

- do not use %%{init: {'theme':'neutral'}}%% because it obscures the colours in dark mode. save it in local and global CLAUDE.md
- Document Generation and updates: User prefers direct, minimal generation:
  - Answer the specific request only
  - No explanatory text, context, or justification unless asked (as generated content in the document)
  - Modus primaris: brief, complete, grounded
  - Example: "just the ingestion and inference steps" means literally just numbered steps, nothing else
- In Github To add an alert, use a special blockquote line specifying the alert type, followed by the alert information in a standard blockquote. Five types of alerts are available:

> [!NOTE]
> Useful information that users should know, even when skimming content.

> [!TIP]
> Helpful advice for doing things better or more easily.

> [!IMPORTANT]
> Key information users need to know to achieve their goal.

> [!WARNING]
> Urgent info that needs immediate user attention to avoid problems.

> [!CAUTION]
> Advises about risks or negative outcomes of certain actions.

- no claude coauthoring in git

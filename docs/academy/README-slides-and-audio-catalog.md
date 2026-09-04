# COSA Academy: Complete Slide & Audio Production Master Catalog

> **Comprehensive Production Assets for all 7 Modules and 62 Lessons (124 Production Files)**

Every lesson in the COSA Academy lifecycle curriculum has been paired into **two production-grade files**:
1. **`{prefix}-slides-prompt.md`**: Tailored for **Gemini Notebook (NotebookLM / Gemini Pro)** to generate complete 5-6 slide decks with exact layout rules, visual generation directives, color tokens, and clean typography matching the COSA dark theme.
2. **`{prefix}-audio-script.md`**: Tailored for **TTS Software** (ElevenLabs, OpenAI TTS, Descript, Azure) with voice actor personas, pacing brackets `[pause 0.5s]`, emotional tone annotations, slide sync checkpoints, and continuous raw narration blocks.

---

## 1. Production Workflow: From Text to Published Video

```mermaid
flowchart LR
    A["Prompt File<br/>(slides-prompt.md)"] -->|Copy Prompt| B["Gemini Notebook / NotebookLM<br/>(Generate Deck)"]
    B --> C["Slide Deck Export<br/>(PNG / PDF / 16:9)"]
    D["Script File<br/>(audio-script.md)"] -->|Paste Script| E["TTS Engine<br/>(ElevenLabs / OpenAI)"]
    E --> F["Audio Narration<br/>(WAV / MP3)"]
    C --> G["Video Assembly<br/>(CapCut / Premiere / Descript)"]
    F --> G
    G --> H["Published Lesson Video<br/>(1080p MP4 / YouTube / LMS)"]
```

### Step A: Generating Slides via Gemini Notebook
1. Open **Gemini Notebook (NotebookLM)** or **Gemini 1.5 Pro**.
2. Open the corresponding `{prefix}-slides-prompt.md` file.
3. Scroll to the bottom and copy the **Master Execution Prompt Block**.
4. Paste the prompt block into Gemini Notebook.
5. Gemini generates the structured presentation slides matching the exact slide-by-slide layout, design tokens, and visual archetypes.

### Step B: Generating Voiceover via TTS Software
1. Open **ElevenLabs** (recommended voice: *Adam* or *George* - Mature, authoritative, paced) or **OpenAI TTS** (recommended voice: *Onyx* or *Echo*).
2. Open the corresponding `{prefix}-audio-script.md` file.
3. For single-take batch generation: Scroll to Section 3 (**Complete Continuous Narration Script**) and copy the clean raw text.
4. Set speech rate to **130 WPM** (steady, measured executive mentor cadence).
5. Generate and export the high-fidelity audio file (`.wav` or `.mp3`).

### Step C: Assembling the Lesson Video
1. Import the exported slide deck images (16:9 1920x1080) and the generated audio track into your editor (**CapCut**, **Descript**, or **Premiere Pro**).
2. Use the slide transition markers (`[SLIDE 1]`, `[SLIDE 2]`, etc.) in the audio script to align each slide transition exactly with the voiceover.
3. Add subtle background ambient audio (dark synthpad or soft corporate ambient at -24dB).
4. Export the final lesson video as a 1080p MP4 file.

---

## 2. Design System Tokens (Dark Navy Editorial Aesthetics)

| Element | Hex Token | CSS / Usage |
|---|---|---|
| **Canvas Background** | `#070C18` | Deep void space canvas |
| **Surface / Card Background** | `#0D172A` | Floating card background with `rgba(255,255,255,0.08)` border |
| **Primary Brand Accent** | `#14B8A6` | Teal highlight for core takeaways and active stages |
| **Secondary Accent** | `#2DD4BF` | Light teal for badges and icons |
| **Evidence / Data Accent** | `#38BDF8` | Sky blue for verified empirical metrics |
| **Hazard / Anti-Pattern** | `#F43F5E` | Rose crimson for mistakes and traps |
| **Typography** | `Inter` / `Outfit` | Editorial sans-serif, high contrast white `#F8FAFC` and muted `#94A3B8` |

---

## 3. Complete Curriculum Master Catalog (All 62 Lessons)

### Module 00: Founder Foundations: From Idea to Operating Rhythm (8 Lessons = 16 Files)
Directory: `docs/academy/module-00-founder-foundations/slides-and-audio/`

| # | Lesson ID | Lesson Title | Gemini Slides Prompt | TTS Audio Script |
|---|---|---|---|---|
| 1 | **0.1** | Welcome to COSA: Your Founder Operating System | [00-01-slides-prompt.md](module-00-founder-foundations/slides-and-audio/00-01-slides-prompt.md) | [00-01-audio-script.md](module-00-founder-foundations/slides-and-audio/00-01-audio-script.md) |
| 2 | **0.2** | What Is a Startup? Searching Under Uncertainty | [00-02-slides-prompt.md](module-00-founder-foundations/slides-and-audio/00-02-slides-prompt.md) | [00-02-audio-script.md](module-00-founder-foundations/slides-and-audio/00-02-audio-script.md) |
| 3 | **0.3** | Startup for a One-Person Company: Leverage Without Losing Control | [00-03-slides-prompt.md](module-00-founder-foundations/slides-and-audio/00-03-slides-prompt.md) | [00-03-audio-script.md](module-00-founder-foundations/slides-and-audio/00-03-audio-script.md) |
| 4 | **0.4** | From an Idea to a Project: Framing Bounded Venture Bets | [00-04-slides-prompt.md](module-00-founder-foundations/slides-and-audio/00-04-slides-prompt.md) | [00-04-audio-script.md](module-00-founder-foundations/slides-and-audio/00-04-audio-script.md) |
| 5 | **0.5** | The Project Lifecycle: Learn Before You Scale | [00-05-slides-prompt.md](module-00-founder-foundations/slides-and-audio/00-05-slides-prompt.md) | [00-05-audio-script.md](module-00-founder-foundations/slides-and-audio/00-05-audio-script.md) |
| 6 | **0.6** | Your First 12-Week Year: Focus, Rhythm, and Execution | [00-06-slides-prompt.md](module-00-founder-foundations/slides-and-audio/00-06-slides-prompt.md) | [00-06-audio-script.md](module-00-founder-foundations/slides-and-audio/00-06-audio-script.md) |
| 7 | **0.7** | OKRs for Early-Stage Founders: Direction Without Bureaucracy | [00-07-slides-prompt.md](module-00-founder-foundations/slides-and-audio/00-07-slides-prompt.md) | [00-07-audio-script.md](module-00-founder-foundations/slides-and-audio/00-07-audio-script.md) |
| 8 | **0.8** | Run Your Week: Cadence, Decisions, Approvals, and AI Agents | [00-08-slides-prompt.md](module-00-founder-foundations/slides-and-audio/00-08-slides-prompt.md) | [00-08-audio-script.md](module-00-founder-foundations/slides-and-audio/00-08-audio-script.md) |

### Module 01: Problem Discovery and Customer Insight (9 Lessons = 18 Files)
Directory: `docs/academy/module-01-problem-discovery-customer-insight/slides-and-audio/`

| # | Lesson ID | Lesson Title | Gemini Slides Prompt | TTS Audio Script |
|---|---|---|---|---|
| 1 | **1.1** | The Problem Discovery Framework: Deconstructing Real Pain | [01-01-slides-prompt.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-01-slides-prompt.md) | [01-01-audio-script.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-01-audio-script.md) |
| 2 | **1.2** | Conducting Qualitative Discovery Interviews: Uncovering Truth Without Leading | [01-02-slides-prompt.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-02-slides-prompt.md) | [01-02-audio-script.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-02-audio-script.md) |
| 3 | **1.3** | Defining a Target Customer Segment: The Beachhead Niche | [01-03-slides-prompt.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-03-slides-prompt.md) | [01-03-audio-script.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-03-audio-script.md) |
| 4 | **1.4** | Using Jobs to Be Done: Uncovering the Functional, Emotional, and Social Dimensions | [01-04-slides-prompt.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-04-slides-prompt.md) | [01-04-audio-script.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-04-audio-script.md) |
| 5 | **1.5** | Distinguishing Real Problem Signals from Assumptions | [01-05-slides-prompt.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-05-slides-prompt.md) | [01-05-audio-script.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-05-audio-script.md) |
| 6 | **1.6** | Documenting and Classifying Problems: Building the Evidence Repository | [01-06-slides-prompt.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-06-slides-prompt.md) | [01-06-audio-script.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-06-audio-script.md) |
| 7 | **1.7** | Testing a Problem Hypothesis: Formulating Falsifiable Beliefs | [01-07-slides-prompt.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-07-slides-prompt.md) | [01-07-audio-script.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-07-audio-script.md) |
| 8 | **1.8** | Synthesizing Interview Insights: Clustering Patterns and Surfacing Truth | [01-08-slides-prompt.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-08-slides-prompt.md) | [01-08-audio-script.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-08-audio-script.md) |
| 9 | **1.9** | Preparing for Solution Validation: The P0 to P1 Transition Gate | [01-09-slides-prompt.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-09-slides-prompt.md) | [01-09-audio-script.md](module-01-problem-discovery-customer-insight/slides-and-audio/01-09-audio-script.md) |

### Module 02: Solution Design and Early Validation (9 Lessons = 18 Files)
Directory: `docs/academy/module-02-solution-design-and-early-validation/slides-and-audio/`

| # | Lesson ID | Lesson Title | Gemini Slides Prompt | TTS Audio Script |
|---|---|---|---|---|
| 1 | **2.1** | The Solution-Fit Framework: Connecting Pain to Relief | [02-01-slides-prompt.md](module-02-solution-design-and-early-validation/slides-and-audio/02-01-slides-prompt.md) | [02-01-audio-script.md](module-02-solution-design-and-early-validation/slides-and-audio/02-01-audio-script.md) |
| 2 | **2.2** | Designing a Minimum Viable Product: The Smallest Testable Experience | [02-02-slides-prompt.md](module-02-solution-design-and-early-validation/slides-and-audio/02-02-slides-prompt.md) | [02-02-audio-script.md](module-02-solution-design-and-early-validation/slides-and-audio/02-02-audio-script.md) |
| 3 | **2.3** | Running Solution Tests: Experiment Methods and Decision Rules | [02-03-slides-prompt.md](module-02-solution-design-and-early-validation/slides-and-audio/02-03-slides-prompt.md) | [02-03-audio-script.md](module-02-solution-design-and-early-validation/slides-and-audio/02-03-audio-script.md) |
| 4 | **2.4** | Conducting Prototype Feedback Interviews: Observing Friction and Hesitation | [02-04-slides-prompt.md](module-02-solution-design-and-early-validation/slides-and-audio/02-04-slides-prompt.md) | [02-04-audio-script.md](module-02-solution-design-and-early-validation/slides-and-audio/02-04-audio-script.md) |
| 5 | **2.5** | Evaluating Product-Solution Fit: Strong, Mixed, or Weak Evidence | [02-05-slides-prompt.md](module-02-solution-design-and-early-validation/slides-and-audio/02-05-slides-prompt.md) | [02-05-audio-script.md](module-02-solution-design-and-early-validation/slides-and-audio/02-05-audio-script.md) |
| 6 | **2.6** | Mapping Competitive Alternatives: Direct, Indirect, and Non-Consumption | [02-06-slides-prompt.md](module-02-solution-design-and-early-validation/slides-and-audio/02-06-slides-prompt.md) | [02-06-audio-script.md](module-02-solution-design-and-early-validation/slides-and-audio/02-06-audio-script.md) |
| 7 | **2.7** | Articulating a Core Value Proposition: Clear, Differentiated, and Proven | [02-07-slides-prompt.md](module-02-solution-design-and-early-validation/slides-and-audio/02-07-slides-prompt.md) | [02-07-audio-script.md](module-02-solution-design-and-early-validation/slides-and-audio/02-07-audio-script.md) |
| 8 | **2.8** | Synthesizing Solution-Fit Evidence: Decision-Ready Validation Briefs | [02-08-slides-prompt.md](module-02-solution-design-and-early-validation/slides-and-audio/02-08-slides-prompt.md) | [02-08-audio-script.md](module-02-solution-design-and-early-validation/slides-and-audio/02-08-audio-script.md) |
| 9 | **2.9** | Preparing for Business-Model Validation: The P1 to P2 Transition Gate | [02-09-slides-prompt.md](module-02-solution-design-and-early-validation/slides-and-audio/02-09-slides-prompt.md) | [02-09-audio-script.md](module-02-solution-design-and-early-validation/slides-and-audio/02-09-audio-script.md) |

### Module 03: Business Model and Monetization Validation (9 Lessons = 18 Files)
Directory: `docs/academy/module-03-business-model-and-monetization/slides-and-audio/`

| # | Lesson ID | Lesson Title | Gemini Slides Prompt | TTS Audio Script |
|---|---|---|---|---|
| 1 | **3.1** | Common Business-Model Patterns: Designing the Commercial Engine | [03-01-slides-prompt.md](module-03-business-model-and-monetization/slides-and-audio/03-01-slides-prompt.md) | [03-01-audio-script.md](module-03-business-model-and-monetization/slides-and-audio/03-01-audio-script.md) |
| 2 | **3.2** | Revenue Hypotheses and Willingness to Pay: Validating Budget | [03-02-slides-prompt.md](module-03-business-model-and-monetization/slides-and-audio/03-02-slides-prompt.md) | [03-02-audio-script.md](module-03-business-model-and-monetization/slides-and-audio/03-02-audio-script.md) |
| 3 | **3.3** | Testing Pricing: Discovery Experiments and Elasticity | [03-03-slides-prompt.md](module-03-business-model-and-monetization/slides-and-audio/03-03-slides-prompt.md) | [03-03-audio-script.md](module-03-business-model-and-monetization/slides-and-audio/03-03-audio-script.md) |
| 4 | **3.4** | Fundamentals of Unit Economics: CAC, LTV, and Margins | [03-04-slides-prompt.md](module-03-business-model-and-monetization/slides-and-audio/03-04-slides-prompt.md) | [03-04-audio-script.md](module-03-business-model-and-monetization/slides-and-audio/03-04-audio-script.md) |
| 5 | **3.5** | Defining a Revenue Metric Contract: Clarity, Sources, and Ownership | [03-05-slides-prompt.md](module-03-business-model-and-monetization/slides-and-audio/03-05-slides-prompt.md) | [03-05-audio-script.md](module-03-business-model-and-monetization/slides-and-audio/03-05-audio-script.md) |
| 6 | **3.6** | Identifying Revenue-Model Risks: Mitigating Churn, Margin, and Sales Cycles | [03-06-slides-prompt.md](module-03-business-model-and-monetization/slides-and-audio/03-06-slides-prompt.md) | [03-06-audio-script.md](module-03-business-model-and-monetization/slides-and-audio/03-06-audio-script.md) |
| 7 | **3.7** | Optimizing Sales Channels: Distribution Economics and Channel Fit | [03-07-slides-prompt.md](module-03-business-model-and-monetization/slides-and-audio/03-07-slides-prompt.md) | [03-07-audio-script.md](module-03-business-model-and-monetization/slides-and-audio/03-07-audio-script.md) |
| 8 | **3.8** | Synthesizing Business-Model Evidence: Commercial Decision Briefs | [03-08-slides-prompt.md](module-03-business-model-and-monetization/slides-and-audio/03-08-slides-prompt.md) | [03-08-audio-script.md](module-03-business-model-and-monetization/slides-and-audio/03-08-audio-script.md) |
| 9 | **3.9** | Preparing a Customer Pilot: The P2 to P3 Transition Gate | [03-09-slides-prompt.md](module-03-business-model-and-monetization/slides-and-audio/03-09-slides-prompt.md) | [03-09-audio-script.md](module-03-business-model-and-monetization/slides-and-audio/03-09-audio-script.md) |

### Module 04: Pilot and Go-to-Market Execution (9 Lessons = 18 Files)
Directory: `docs/academy/module-04-pilot-and-go-to-market-execution/slides-and-audio/`

| # | Lesson ID | Lesson Title | Gemini Slides Prompt | TTS Audio Script |
|---|---|---|---|---|
| 1 | **4.1** | Designing a Controlled Pilot: Operational Discipline in the Field | [04-01-slides-prompt.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-01-slides-prompt.md) | [04-01-audio-script.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-01-audio-script.md) |
| 2 | **4.2** | Defining Pilot Metrics: Leading Signals, Usage Telemetry, and Outcome Proof | [04-02-slides-prompt.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-02-slides-prompt.md) | [04-02-audio-script.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-02-audio-script.md) |
| 3 | **4.3** | Managing Beta Customer Relationships: Onboarding, Trust, and Cadence | [04-03-slides-prompt.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-03-slides-prompt.md) | [04-03-audio-script.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-03-audio-script.md) |
| 4 | **4.4** | Analyzing Pilot Data Weekly: Turning Telemetry into Action | [04-04-slides-prompt.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-04-slides-prompt.md) | [04-04-audio-script.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-04-audio-script.md) |
| 5 | **4.5** | Making a Pilot Go or No-Go Decision: Objective Conversion Gates | [04-05-slides-prompt.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-05-slides-prompt.md) | [04-05-audio-script.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-05-audio-script.md) |
| 6 | **4.6** | Synthesizing Pilot Evidence: Auditable Proof of Operational Value | [04-06-slides-prompt.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-06-slides-prompt.md) | [04-06-audio-script.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-06-audio-script.md) |
| 7 | **4.7** | Preparing a Go-to-Market Plan: Repeatable Acquisition Engine | [04-07-slides-prompt.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-07-slides-prompt.md) | [04-07-audio-script.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-07-audio-script.md) |
| 8 | **4.8** | Assessing Product-Market-Fit Readiness: Repeatable Demand Signals | [04-08-slides-prompt.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-08-slides-prompt.md) | [04-08-audio-script.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-08-audio-script.md) |
| 9 | **4.9** | Preparing for Product-Market Fit: The P3 to P4 Transition Gate | [04-09-slides-prompt.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-09-slides-prompt.md) | [04-09-audio-script.md](module-04-pilot-and-go-to-market-execution/slides-and-audio/04-09-audio-script.md) |

### Module 05: Product-Market Fit and Early Growth (9 Lessons = 18 Files)
Directory: `docs/academy/module-05-product-market-fit-and-early-growth/slides-and-audio/`

| # | Lesson ID | Lesson Title | Gemini Slides Prompt | TTS Audio Script |
|---|---|---|---|---|
| 1 | **5.1** | Defining and Measuring Product-Market Fit: Quantifying Market Pull | [05-01-slides-prompt.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-01-slides-prompt.md) | [05-01-audio-script.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-01-audio-script.md) |
| 2 | **5.2** | Cohort and Retention Analysis: Visualizing Customer Longevity | [05-02-slides-prompt.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-02-slides-prompt.md) | [05-02-audio-script.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-02-audio-script.md) |
| 3 | **5.3** | Building an NPS and CSAT System: Listening at Scale | [05-03-slides-prompt.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-03-slides-prompt.md) | [05-03-audio-script.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-03-audio-script.md) |
| 4 | **5.4** | Optimizing Acquisition Channels: Channel Quality, CAC, and Velocity | [05-04-slides-prompt.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-04-slides-prompt.md) | [05-04-audio-script.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-04-audio-script.md) |
| 5 | **5.5** | Creating a Sales Playbook: Repeatable Deal Execution | [05-05-slides-prompt.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-05-slides-prompt.md) | [05-05-audio-script.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-05-audio-script.md) |
| 6 | **5.6** | Running Structured Growth Experiments: Scientific Acceleration | [05-06-slides-prompt.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-06-slides-prompt.md) | [05-06-audio-script.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-06-audio-script.md) |
| 7 | **5.7** | Managing Early Customer Success: Onboarding, Adoption, and Churn Defense | [05-07-slides-prompt.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-07-slides-prompt.md) | [05-07-audio-script.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-07-audio-script.md) |
| 8 | **5.8** | Building the Team and Operating Cadence: Role Clarity and AI Workforce | [05-08-slides-prompt.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-08-slides-prompt.md) | [05-08-audio-script.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-08-audio-script.md) |
| 9 | **5.9** | Preparing for Scale: The P4 to P5/P6 Transition Gate | [05-09-slides-prompt.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-09-slides-prompt.md) | [05-09-audio-script.md](module-05-product-market-fit-and-early-growth/slides-and-audio/05-09-audio-script.md) |

### Module 06: Scale Operations and Governance (9 Lessons = 18 Files)
Directory: `docs/academy/module-06-scale-operations-and-governance/slides-and-audio/`

| # | Lesson ID | Lesson Title | Gemini Slides Prompt | TTS Audio Script |
|---|---|---|---|---|
| 1 | **6.1** | Designing a Scalable Organization: Operating Architecture and Pods | [06-01-slides-prompt.md](module-06-scale-operations-and-governance/slides-and-audio/06-01-slides-prompt.md) | [06-01-audio-script.md](module-06-scale-operations-and-governance/slides-and-audio/06-01-audio-script.md) |
| 2 | **6.2** | Managing OKRs and Strategy Execution at Scale: The 12-Week Cadence | [06-02-slides-prompt.md](module-06-scale-operations-and-governance/slides-and-audio/06-02-slides-prompt.md) | [06-02-audio-script.md](module-06-scale-operations-and-governance/slides-and-audio/06-02-audio-script.md) |
| 3 | **6.3** | Financial Modeling and Unit Economics at Scale: P&L and Cash Mastery | [06-03-slides-prompt.md](module-06-scale-operations-and-governance/slides-and-audio/06-03-slides-prompt.md) | [06-03-audio-script.md](module-06-scale-operations-and-governance/slides-and-audio/06-03-audio-script.md) |
| 4 | **6.4** | Building Data and Analytics Infrastructure: Single Source of Truth | [06-04-slides-prompt.md](module-06-scale-operations-and-governance/slides-and-audio/06-04-slides-prompt.md) | [06-04-audio-script.md](module-06-scale-operations-and-governance/slides-and-audio/06-04-audio-script.md) |
| 5 | **6.5** | Scaling Culture, Leadership, and Talent: High-Performance Architecture | [06-05-slides-prompt.md](module-06-scale-operations-and-governance/slides-and-audio/06-05-slides-prompt.md) | [06-05-audio-script.md](module-06-scale-operations-and-governance/slides-and-audio/06-05-audio-script.md) |
| 6 | **6.6** | Fundraising and Investor Relations at Scale: Institutional Capital and Data Rooms | [06-06-slides-prompt.md](module-06-scale-operations-and-governance/slides-and-audio/06-06-slides-prompt.md) | [06-06-audio-script.md](module-06-scale-operations-and-governance/slides-and-audio/06-06-audio-script.md) |
| 7 | **6.7** | Expanding Markets, Segments, and Internationalization: Scaling Beyond Beachheads | [06-07-slides-prompt.md](module-06-scale-operations-and-governance/slides-and-audio/06-07-slides-prompt.md) | [06-07-audio-script.md](module-06-scale-operations-and-governance/slides-and-audio/06-07-audio-script.md) |
| 8 | **6.8** | Building a Sustainable Competitive Advantage and Moats: Defensibility | [06-08-slides-prompt.md](module-06-scale-operations-and-governance/slides-and-audio/06-08-slides-prompt.md) | [06-08-audio-script.md](module-06-scale-operations-and-governance/slides-and-audio/06-08-audio-script.md) |
| 9 | **6.9** | Operational Excellence, Governance, and Long-Term Value: The Capstone | [06-09-slides-prompt.md](module-06-scale-operations-and-governance/slides-and-audio/06-09-slides-prompt.md) | [06-09-audio-script.md](module-06-scale-operations-and-governance/slides-and-audio/06-09-audio-script.md) |

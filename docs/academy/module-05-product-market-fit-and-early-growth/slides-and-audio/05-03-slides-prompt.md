# Gemini Notebook Slide Generation Prompt: Lesson 5.3 — Building an NPS and CSAT System: Listening at Scale
> **Module**: 05 — Product-Market Fit and Early Growth
> **Lifecycle Stage**: `P4_PMF_EARLY_GROWTH` | **Lesson Slug**: `p4-m5-l03`
> **Output Format**: 16:9 High-Impact Presentation Deck (6 Slides)

---

## INSTRUCTIONS FOR GEMINI / NOTEBOOKLM
You are acting as a Principal Venture Architect and World-Class Slide Designer for the **COSA Founder Operating System**.
Generate a polished, production-grade 6-slide presentation deck for **Lesson 5.3: Building an NPS and CSAT System: Listening at Scale**.
Follow the exact design system tokens, layout wireframes, copy structure, and visual prompts provided below.

### MASTER VISUAL DIRECTIVE & DESIGN SYSTEM (COSA Dark Canvas)
- **Aspect Ratio**: 16:9 Widescreen
- **Color Tokens**:
  - `Background Canvas`: `#070C18` (Deep navy void)
  - `Radial Accent / Ambient Glow`: `#0B1934` (Subtle depth behind central cards)
  - `Surface / Container Fill`: `#0D172A` with subtle outline `1px solid rgba(255, 255, 255, 0.08)`
  - `Primary Highlight`: `#14B8A6` (COSA Teal - Progress, key concepts, actionable levers)
  - `Secondary Signal`: `#38BDF8` (Sky Blue - Evidence, empirical validation, customer data)
  - `Warning / Anti-Pattern`: `#F43F5E` (Rose / Crimson - Assumptions, pitfalls, vanity metrics)
  - `Typography Primary`: `#FFFFFF` (Headers, bold takeaways)
  - `Typography Secondary`: `#E2E8F0` (Body text, data points)
  - `Typography Muted`: `#94A3B8` (Footnotes, captions, supporting labels)
- **Typography**: Modern geometric sans-serif (Inter, Outfit, or SF Pro Display). Clean weights (Bold 700 for titles, Medium 500 for cards, Regular 400 for copy).
- **Layout Philosophy**: Editorial minimalism. High whitespace, strong visual hierarchy, stark contrast.
- **Critical Negative Constraints**:
  - NEVER generate fake, cluttered software dashboards or generic SaaS UI mockups.
  - NEVER use childish cartoons, stock corporate 3D clay figures, or clip art.
  - Maintain crisp card containers, clear directional node diagrams, and high-impact data callouts.


---

## SLIDE-BY-SLIDE SPECIFICATIONS

### Slide 1: Title & Core Thesis (Hero Presentation)
- **Visual Archetype**: `SL-01 — Takeaway Claim`
- **Layout & Composition**: Hero layout with glowing customer sentiment waveform on #070C18 canvas.
- **Header Badge**: `COSA ACADEMY · MODULE 05 · LESSON 5.3`
- **Main Headline**: **Building an NPS and CSAT System: Closing the Loop**
- **Sub-headline / Thesis**: A customer feedback score is useless theater unless it triggers structured qualitative follow-ups and rapid operational improvements.
- **Core Slide Content**:
  - Net Promoter Score (NPS) measures long-term brand loyalty; Customer Satisfaction (CSAT) measures specific transactional interactions.
  - The number alone does not matter; what matters is the verbatim qualitative explanation behind the score.
  - A high-performing feedback system establishes a closed loop: Detractors are contacted within 24 hours, Promoters are mobilized for referrals.
- **Highlight / Accent Box**: FEEDBACK LAW: If you collect customer scores without following up on negative feedback, you actively decrease customer trust.
- **Diagram / Visual Structure**: Visual sentiment spectrum: A glowing horizontal score dial from 0 to 10 on dark canvas, highlighting Promoters in neon teal and Detractors in vibrant rose.
- **AI Visual Generation Directive**: *Stylized customer sentiment gauge on dark canvas #070C18: glowing arc from 0 to 10, with red Detractor zone (0-6), amber Passive zone (7-8), and neon teal Promoter zone (9-10).*

### Slide 2: NPS vs. CSAT Deconstructed (Taxonomy & Protocol)
- **Visual Archetype**: `SL-02 — Definition Contrast`
- **Layout & Composition**: Two-card comparative breakdown detailing NPS vs. CSAT.
- **Header Badge**: `MEASUREMENT ARCHITECTURE`
- **Main Headline**: **Relational Loyalty (NPS) vs. Transactional Delight (CSAT)**
- **Sub-headline / Thesis**: Knowing when, where, and how to deploy each survey primitive.
- **Core Slide Content**:
  - Net Promoter Score (NPS): 'On a scale of 0-10, how likely are you to recommend COSA to a colleague?' (Deployed quarterly; measures relational loyalty).
  - Customer Satisfaction (CSAT): 'How satisfied were you with this specific support resolution / feature import?' (Deployed immediately after a specific workflow).
  - The Complementary Role: CSAT pinpoints micro-interaction bugs; NPS measures overall business health and retention risk.
- **Highlight / Accent Box**: SCORING FORMULA: NPS = % Promoters (9-10) minus % Detractors (0-6). A score >+50 is excellent in B2B SaaS.
- **Diagram / Visual Structure**: Split card: Left card showing glowing teal NPS megaphone; right card showing glowing cyan CSAT five-star rating widget.
- **AI Visual Generation Directive**: *Two column contrast cards on deep navy: Left shows quarterly loyalty radar; right shows instant post-action rating stars.*

### Slide 3: The Closed-Loop Feedback Protocol (Operating Workflow)
- **Visual Archetype**: `SL-03 — Operating Loop`
- **Layout & Composition**: 3-branch operational response flowchart.
- **Header Badge**: `CLOSED-LOOP WORKFLOW`
- **Main Headline**: **The Closed-Loop Response Protocol**
- **Sub-headline / Thesis**: How your team takes immediate action based on incoming customer survey scores.
- **Core Slide Content**:
  - Detractors (Score 0-6) → Immediate 24h Triage: Personal founder email or phone call: 'I saw your score. What broke, and how can we make it right?'
  - Passives (Score 7-8) → The Competitive Vulnerability: Ask: 'What is the one missing feature that would make this a 10 for you?'
  - Promoters (Score 9-10) → The Referral Engine: Thank them and prompt: 'Would you be willing to leave a review on G2 or introduce one colleague?'
- **Highlight / Accent Box**: CONVERSION PROTOCOL: Turn your Promoters into an active unpaid sales force through automated referral prompts.
- **Diagram / Visual Structure**: Three-branch decision flowchart with color-coded response cards for Red Detractors, Amber Passives, and Green Promoters.
- **AI Visual Generation Directive**: *Flowchart on dark canvas #070C18: incoming score splitting into three branches: Crimson phone triage, Amber survey prompt, and Teal referral link.*

### Slide 4: Feedback Workflows in COSA Workspace (COSA Workspace Integration)
- **Visual Archetype**: `SL-05 — Example Artifact`
- **Layout & Composition**: UI card preview of COSA Feedback Automation Workflow.
- **Header Badge**: `COSA IMPLEMENTATION`
- **Main Headline**: **Automating Feedback in COSA Workflows**
- **Sub-headline / Thesis**: Triggering surveys, tagging sentiment, and assigning triage tasks automatically.
- **Core Slide Content**:
  - Automated Survey Triggers: Schedules quarterly NPS emails and in-app CSAT popups after key workflow completions.
  - Detractor Alert Webhook: Automatically creates an urgent P1 task in Tasks whenever a score of ≤6 is logged.
  - Sentiment Analytics: AI agent in Vault clusters verbatim survey comments into recurring product complaints.
- **Highlight / Accent Box**: SYSTEM INTEGRATION: Directly connects customer feedback scores to customer retention health cards in Sales CRM.
- **Diagram / Visual Structure**: Mockup of COSA Feedback Dashboard with live NPS meter (+54), sentiment comment stream, and detractor task queue.
- **AI Visual Generation Directive**: *Modern UI layout on dark slate #070C18, showing live NPS meter at +54, sentiment quote chips, and urgent 'Contact Detractor' task button.*

### Slide 5: Anti-Patterns vs. Best Practices (Comparative Matrix)
- **Visual Archetype**: `SL-06 — Decision Checkpoint`
- **Layout & Composition**: Side-by-side comparison table.
- **Header Badge**: `FEEDBACK PITFALLS`
- **Main Headline**: **Vanity Surveying vs. Actionable Governance**
- **Sub-headline / Thesis**: Avoiding the common survey mistakes that annoy customers.
- **Core Slide Content**:
  - Trap: Begging customers for high scores: 'If you loved this, please give us a 10!' (Destroys data integrity).
  - Trap: Hiding detractor feedback from the engineering team to make quarterly reporting look rosy.
  - Best Practice: Welcome detractor feedback as a free roadmap audit. Detractors tell you exactly where your product is bleeding.
- **Highlight / Accent Box**: DECISION CHECKPOINT: Every detractor who takes the time to complain is a customer who still cares. The ones who say nothing are already gone.
- **Diagram / Visual Structure**: Table comparing score-gaming tactics with genuine feedback governance.
- **AI Visual Generation Directive**: *Comparison table on dark canvas: red hazard badges next to survey begging; teal checkmarks next to rigorous detractor follow-up routines.*

### Slide 6: Founder Action Checkpoint (Action Deliverable)
- **Visual Archetype**: `SL-07 — Learner Action`
- **Layout & Composition**: Action deliverable card container.
- **Header Badge**: `EXERCISE: FEEDBACK WORKFLOW`
- **Main Headline**: **Deploy Your Automated Feedback System in COSA**
- **Sub-headline / Thesis**: Configure your quarterly NPS survey and automated detractor triage workflow.
- **Core Slide Content**:
  - Step 1: Open COSA Workflows and initialize the NPS Feedback Engine.
  - Step 2: Set your Quarterly Survey Cadence and customize your follow-up questions.
  - Step 3: Connect your Detractor Alert trigger to create high-priority tasks in Tasks.
  - Step 4: Establish your Promoter Referral email template in Sales CRM.
- **Highlight / Accent Box**: DELIVERABLE: Verify that your Closed-Loop Detractor triage task triggers automatically upon receiving a test score of 5.
- **Diagram / Visual Structure**: Interactive card preview showing completed feedback engine setup with glowing test trigger button on dark container.
- **AI Visual Generation Directive**: *Clean digital card preview on dark navy #070C18, showing configured NPS workflow with glowing teal 'Test Trigger' button.*

---

## GEMINI NOTEBOOK COPY-PASTE PROMPT EXECUTION
```text
Create a 6-slide executive presentation for Lesson 5.3: 'Building an NPS and CSAT System: Listening at Scale' in the COSA dark canvas style (#070C18 canvas, #14B8A6 teal primary accent, #38BDF8 sky blue evidence, #F43F5E risk accent).
Include clean card containers, clear typography, and avoid fake UI clutter. Structure each slide strictly according to the following specifications:

[SLIDE 1 - TITLE & CORE THESIS]
Badge: COSA ACADEMY · MODULE 05 · LESSON 5.3
Headline: Building an NPS and CSAT System: Closing the Loop
Key Points:
- Net Promoter Score (NPS) measures long-term brand loyalty; Customer Satisfaction (CSAT) measures specific transactional interactions.
- The number alone does not matter; what matters is the verbatim qualitative explanation behind the score.
- A high-performing feedback system establishes a closed loop: Detractors are contacted within 24 hours, Promoters are mobilized for referrals.
Callout: FEEDBACK LAW: If you collect customer scores without following up on negative feedback, you actively decrease customer trust.

[SLIDE 2 - NPS VS. CSAT DECONSTRUCTED]
Badge: MEASUREMENT ARCHITECTURE
Headline: Relational Loyalty (NPS) vs. Transactional Delight (CSAT)
Key Points:
- Net Promoter Score (NPS): 'On a scale of 0-10, how likely are you to recommend COSA to a colleague?' (Deployed quarterly; measures relational loyalty).
- Customer Satisfaction (CSAT): 'How satisfied were you with this specific support resolution / feature import?' (Deployed immediately after a specific workflow).
- The Complementary Role: CSAT pinpoints micro-interaction bugs; NPS measures overall business health and retention risk.
Callout: SCORING FORMULA: NPS = % Promoters (9-10) minus % Detractors (0-6). A score >+50 is excellent in B2B SaaS.

[SLIDE 3 - THE CLOSED-LOOP FEEDBACK PROTOCOL]
Badge: CLOSED-LOOP WORKFLOW
Headline: The Closed-Loop Response Protocol
Key Points:
- Detractors (Score 0-6) → Immediate 24h Triage: Personal founder email or phone call: 'I saw your score. What broke, and how can we make it right?'
- Passives (Score 7-8) → The Competitive Vulnerability: Ask: 'What is the one missing feature that would make this a 10 for you?'
- Promoters (Score 9-10) → The Referral Engine: Thank them and prompt: 'Would you be willing to leave a review on G2 or introduce one colleague?'
Callout: CONVERSION PROTOCOL: Turn your Promoters into an active unpaid sales force through automated referral prompts.

[SLIDE 4 - FEEDBACK WORKFLOWS IN COSA WORKSPACE]
Badge: COSA IMPLEMENTATION
Headline: Automating Feedback in COSA Workflows
Key Points:
- Automated Survey Triggers: Schedules quarterly NPS emails and in-app CSAT popups after key workflow completions.
- Detractor Alert Webhook: Automatically creates an urgent P1 task in Tasks whenever a score of ≤6 is logged.
- Sentiment Analytics: AI agent in Vault clusters verbatim survey comments into recurring product complaints.
Callout: SYSTEM INTEGRATION: Directly connects customer feedback scores to customer retention health cards in Sales CRM.

[SLIDE 5 - ANTI-PATTERNS VS. BEST PRACTICES]
Badge: FEEDBACK PITFALLS
Headline: Vanity Surveying vs. Actionable Governance
Key Points:
- Trap: Begging customers for high scores: 'If you loved this, please give us a 10!' (Destroys data integrity).
- Trap: Hiding detractor feedback from the engineering team to make quarterly reporting look rosy.
- Best Practice: Welcome detractor feedback as a free roadmap audit. Detractors tell you exactly where your product is bleeding.
Callout: DECISION CHECKPOINT: Every detractor who takes the time to complain is a customer who still cares. The ones who say nothing are already gone.

[SLIDE 6 - FOUNDER ACTION CHECKPOINT]
Badge: EXERCISE: FEEDBACK WORKFLOW
Headline: Deploy Your Automated Feedback System in COSA
Key Points:
- Step 1: Open COSA Workflows and initialize the NPS Feedback Engine.
- Step 2: Set your Quarterly Survey Cadence and customize your follow-up questions.
- Step 3: Connect your Detractor Alert trigger to create high-priority tasks in Tasks.
- Step 4: Establish your Promoter Referral email template in Sales CRM.
Callout: DELIVERABLE: Verify that your Closed-Loop Detractor triage task triggers automatically upon receiving a test score of 5.
```
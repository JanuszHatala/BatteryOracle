# AI Configuration Audit & Markdown Presentation Improvement Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the unformatted, flattened AI Configuration & Doze Audit report (and comparison audits) into a polished, structured presentation with syntax-highlighted copyable block code, interactive ADB command chips, cleanly bordered tables, and crisp typographic hierarchy.

**Architecture:** Create a unified, reusable `MarkdownView` component in `frontend/src/components/ui/MarkdownView.tsx` that equips `ReactMarkdown` + `remark-gfm` with full styling for code blocks (`CodeBlock.tsx`), responsive styled GFM tables, headings, callout blockquotes, and lists. Deploy this component to `DeviceProfileView.tsx` and related markdown views. Enhance prompt instructions in `llm_manager.py` to ensure LLM outputs always use fenced code blocks for commands.

**Tech Stack:** React 19, TypeScript, Tailwind CSS v4, `react-markdown`, `remark-gfm`, Lucide icons, Python FastAPI backend.

---

## Global Constraints
- Strictly avoid removing existing logic or breaking existing component APIs.
- Preserve Tailwind v4 conventions (no invalid `@tailwindcss/typography` dependencies unless natively configured).
- All command blocks and inline ADB commands must provide one-click copy functionality.
- Tables must be wrapped in responsive horizontal scrolling containers to prevent viewport clipping.
- Do not use em-dashes (`—`) in user-facing texts; use standard hyphens (`-`) or colons per user instructions.

## Review Focus
1. **Existing saved audit reports:** Profiles already generated and stored in SQLite (like the user's Pixel 10 Pro profile) must immediately render properly without requiring a re-run.
2. **GFM tables with emojis / long texts:** Tables containing complex text, emojis, and status badges must not wrap into chaotic vertical strips or bleed off-screen.
3. **Inline vs block commands:** Inline commands (e.g. `` `adb shell dumpsys ...` `` in bullet points) should render as copyable interactive chips, while multi-line commands must render as full fenced blocks with header bars.
4. **Exported Markdown integrity:** The "Export .md" button should continue to export the pristine raw markdown unchanged.
5. **Comparison & Synthesis consistency:** Ensure the same formatting quality in the Profile Comparison view and Master Synthesis view.

---

## Proposed Changes

### Frontend Component Architecture

#### [NEW] `frontend/src/components/ui/MarkdownView.tsx`
Create a dedicated, reusable markdown renderer component:
- Wraps `ReactMarkdown` with `remarkGfm`.
- Integrates `MarkdownCode` and `MarkdownPre` from `CodeBlock.tsx` for terminal icons, copy buttons, line counts, and inline ADB chips.
- Custom table components (`table`, `thead`, `tbody`, `tr`, `th`, `td`) with dark slate borders (`border-slate-800`), zebra striping, padding, and an `overflow-x-auto` wrapper.
- Typographic hierarchy: styled `h1`, `h2`, `h3`, `h4`, `p`, `ul`, `ol`, `li`, `blockquote`, `hr`, `strong`.
- Optional `compact` prop to support tighter spacing in chat cards or dialogs.

```tsx
interface MarkdownViewProps {
  content: string;
  className?: string;
  compact?: boolean;
}
```

#### [MODIFY] `frontend/src/components/profiles/DeviceProfileView.tsx`
- Replace raw `<ReactMarkdown remarkPlugins={[remarkGfm]}>` in the **AI Configuration & Doze Audit** card (lines 1046-1050) with `<MarkdownView content={activeProfile.analysis_text} />`.
- Replace raw `<ReactMarkdown>` in the **AI Configuration Diff Analysis (Comparison tab)** (lines 756-760) with `<MarkdownView content={compareAuditMarkdown} />`.

#### [MODIFY] `frontend/src/components/synthesis/MasterSynthesisView.tsx`
- Replace raw `<ReactMarkdown remarkPlugins={[remarkGfm]}>` in line 226 with `<MarkdownView content={data.synthesis_text} />`.

#### [MODIFY] `frontend/src/components/reports/ComparativeView.tsx`
- Replace raw `<ReactMarkdown remarkPlugins={[remarkGfm]}>` in line 179 with `<MarkdownView content={result.analysis} />`.

---

### Backend Prompt & Sanitization

#### [MODIFY] `llm_manager.py`
- In `profile_audit` prompt template (around line 299):
  - Explicitly mandate that all ADB commands, shell scripts, and maintenance instructions MUST be formatted in fenced markdown code blocks with bash highlighting (```` ```bash ... ``` ````).
  - Explicitly mandate GitHub Flavored Markdown table format for trade-off and tuning matrices.
- In `profile_comparison` prompt template (around line 334):
  - Apply the same formatting enforcements.

#### [NEW] `tests/test_markdown_audit.py`
- Test that verifies `llm_manager.get_prompt_template("profile_audit")` contains strict fenced code block and table formatting instructions.
- Test that verifies `parser.sanitize_ai_output` preserves fenced code blocks and markdown tables cleanly.

---

## Step-by-Step Implementation Tasks

### Task 1: Create Reusable `MarkdownView` Component
**Files:**
- Create: `frontend/src/components/ui/MarkdownView.tsx`
- Reference: `frontend/src/components/ui/CodeBlock.tsx`

- [ ] **Step 1: Implement `MarkdownView` with full GFM element coverage**
  - Implement styled wrappers for:
    - `table`: `<div className="overflow-x-auto my-3 rounded-lg border border-slate-800 bg-slate-950/70 shadow-sm"><table className="w-full text-left text-xs border-collapse">...</table></div>`
    - `thead`: `<thead className="bg-slate-900/90 text-slate-200 font-semibold border-b border-slate-800">`
    - `th`: `<th className="px-3.5 py-2.5 text-slate-200 font-semibold text-xs tracking-wider border-r border-slate-800 last:border-r-0">`
    - `td`: `<td className="px-3.5 py-2 text-slate-300 text-xs border-t border-slate-800/60 border-r border-slate-800/40 last:border-r-0 leading-relaxed align-top">`
    - `tr`: `<tr className="hover:bg-slate-900/40 transition-colors">`
    - `h1`: `<h1 className="text-lg font-bold text-slate-100 mt-4 mb-2 pb-1 border-b border-slate-800 flex items-center gap-2">`
    - `h2`: `<h2 className="text-base font-bold text-slate-100 mt-3.5 mb-1.5 flex items-center gap-2">`
    - `h3`: `<h3 className="text-sm font-semibold text-slate-200 mt-3 mb-1.5 flex items-center gap-1.5">`
    - `h4`: `<h4 className="text-xs font-semibold text-slate-300 mt-2.5 mb-1">`
    - `p`: `<p className="text-xs md:text-sm text-slate-300 leading-relaxed mb-2.5 last:mb-0">`
    - `ul`: `<ul className="list-disc pl-5 space-y-1.5 my-2 text-slate-300 text-xs md:text-sm">`
    - `ol`: `<ol className="list-decimal pl-5 space-y-1.5 my-2 text-slate-300 text-xs md:text-sm">`
    - `li`: `<li className="text-slate-300 leading-relaxed">`
    - `blockquote`: `<blockquote className="border-l-2 border-indigo-500 bg-indigo-950/20 px-3.5 py-2 my-2.5 rounded-r-lg text-slate-300 italic text-xs">`
    - `hr`: `<hr className="my-3.5 border-slate-800" />`
    - `code`: `MarkdownCode`
    - `pre`: `MarkdownPre`
- [ ] **Step 2: Export `MarkdownView` from `frontend/src/components/ui/`**

### Task 2: Integrate `MarkdownView` in `DeviceProfileView.tsx` & Views
**Files:**
- Modify: `frontend/src/components/profiles/DeviceProfileView.tsx`
- Modify: `frontend/src/components/synthesis/MasterSynthesisView.tsx`
- Modify: `frontend/src/components/reports/ComparativeView.tsx`

- [ ] **Step 1: Replace raw ReactMarkdown in `DeviceProfileView.tsx`**
  - Line 1046: Update AI Audit card to use `<MarkdownView content={activeProfile.analysis_text} />`.
  - Line 757: Update Compare Audit tab to use `<MarkdownView content={compareAuditMarkdown} />`.
- [ ] **Step 2: Replace raw ReactMarkdown in `MasterSynthesisView.tsx` and `ComparativeView.tsx`**
- [ ] **Step 3: Run `npm run build` in `frontend` to verify TypeScript and bundling**

### Task 3: Strengthen Backend Audit Prompt Guidelines
**Files:**
- Modify: `llm_manager.py`
- Create: `tests/test_markdown_audit.py`

- [ ] **Step 1: Add unit test in `tests/test_markdown_audit.py`**
  - Verify that `profile_audit` and `profile_comparison` templates explicitly contain code block guidelines (`bash` code blocks) and GFM table standards.
  - Verify that `sanitize_ai_output` retains fenced blocks and pipe tables.
- [ ] **Step 2: Run pytest to see it fail or pass**
- [ ] **Step 3: Update `profile_audit` and `profile_comparison` in `llm_manager.py`**
- [ ] **Step 4: Re-run pytest to verify all tests pass**

---

## Verification Plan

### Automated Verification
```bash
# 1. Frontend compilation & typecheck
cd /Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle/frontend
npm run build

# 2. Backend unit test suite
cd /Users/jh/DevWorkspaces/jh/ProjektyIT/Android/BatteryOracle
.venv/bin/pytest tests/
```

### Manual Verification
1. Open the BatteryOracle web interface (`http://localhost:5173` or `http://localhost:8000`).
2. Navigate to the **Device Profiles** view.
3. Select the Pixel 10 Pro profile (profile 16 from the screenshot).
4. Verify that:
   - Headers (`1. 🛡️ Power Management Posture Summary`, etc.) are rendered with distinct sizing and bold weight.
   - The tuning trade-off table renders with borders, background header styling, and structured columns (`Task`, `Action`, `⚠️ Usability & Comfort Impact`).
   - The ADB commands (`adb shell dumpsys deviceidle whitelist...`, `adb shell cmd appops set...`) render inside dark code block boxes with language tag, line count, and a working **Copy** button.
   - Inline commands render as distinct interactive chips.
   - The "Export .md" button continues to download the complete raw markdown document.

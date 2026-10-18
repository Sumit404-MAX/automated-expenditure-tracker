---
name: Sprint Kanban Task
about: Standardized 6-Stage Gemini Workflow task card for Sumit, Anuj, Saurabh, or Uday
title: "[S0-00] Task Title"
labels: []
assignees: []
---

### 1. Task Metadata
- **Task ID:** `S_-__`
- **Sprint:** `Sprint _`
- **Owner & Role:** 
- **Git Branch to Create (off `dev`):** `git checkout dev && git pull origin dev && git checkout -b feature/...`
- **Allowed Folder to Edit:** `src/...`

### 2. Objective & Acceptance Criteria
- 

### 3. 6-Stage Gemini Execution Checklist
- [ ] **Stage 1 (Intake):** Give this task to Gemini to trigger role skill & sub-task breakdown
- [ ] **Stage 2 (Drive Task Living Doc):** Paste link to created Google Drive Task Living Doc in a comment below
- [ ] **Stage 3 (Implementation):** Write modular code inside owned directory on feature branch
- [ ] **Stage 4 (Objective Testing):** Run local verification test against mock data (`seed_mock_data.py`)
- [ ] **Stage 5 (Systematic Bug-Fix):** Log any errors & fixes in the Drive Task Living Doc
- [ ] **Stage 6 (Commit & PR to `dev`):** Open PR into `dev` with `Closes #<this-issue-number>`

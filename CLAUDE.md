# Project Instructions - Claude Code

> **Note**: This is the main orchestrator file. For detailed guides, see `ClaudeUsage/README.md`

---

## ⚠️ MANDATORY: Read Guides Before Tasks

**YOU MUST read the relevant guide BEFORE starting these tasks. No exceptions.**

| Task | Required Reading | Action |
|------|-----------------|--------|
| **Making ANY commit** | `ClaudeUsage/git_commit_guide.md` | Read FIRST, then commit |
| **Searching 20+ files** | `ClaudeUsage/house_agents.md` | Use house-research agent |
| **Writing tests** | `ClaudeUsage/testing_strategies.md` | Read FIRST, then code |
| **Managing secrets/API keys** | `ClaudeUsage/secrets_management.md` | Read FIRST, then implement |
| **Using UV/dependencies** | `ClaudeUsage/uv_usage.md` | Read FIRST, then modify |
| **Refactoring code** | `ClaudeUsage/code_style_guide.md` | Read FIRST, then refactor |
| **Starting new project** | `ClaudeUsage/project_setup.md` | Read FIRST, then initialize |

**If you skip reading the guide, you're doing it wrong. These are mandatory workflows, not optional documentation.**

---

## Project Purpose
A lightweight, privacy-focused network monitoring tool for macOS that tracks application-level network usage with enhanced domain-level tracking for web browsers. Provides a rich web-based dashboard for visualizing network consumption patterns over time.

## Tech Stack
- Language: Python 3.10+
- Framework: FastAPI
- Key Libraries: Plotly/Dash (visualization), scapy (packet capture), rumps (menubar), SQLite (database), aiosqlite (async DB)
- Package Manager: uv

## Architecture Notes
Single unified Python process (preferred) that handles daemon, web server, and menubar icon. Five main components: (1) Background Daemon for continuous capture, (2) Web Dashboard with FastAPI + Plotly/Dash, (3) SQLite Database for local storage, (4) MenuBar App for quick access, (5) Browser Extension for domain tracking in Zen browser. Privacy-first design with all data staying local (localhost:7500), no external API calls.

---

## Essential Instructions (Always Follow)

### Core Behavior
- Do what has been asked; nothing more, nothing less
- NEVER create files unless absolutely necessary for achieving your goal
- ALWAYS prefer editing existing files to creating new ones
- NEVER proactively create documentation files (*.md) or README files unless explicitly requested

### Naming Conventions
- **Directories**: Use CamelCase (e.g., `VideoProcessor`, `AudioTools`, `DataAnalysis`)
- **Date-based paths**: Use skewer-case with YYYY-MM-DD (e.g., `logs-2025-01-15`, `backup-2025-12-31`)
- **No spaces or underscores** in directory names (except date-based paths)

### TODO Management
- **Always check `TODOS.md` first** when starting a task or session
- **Update immediately** when tasks are completed, added, or changed
- Keep the list current and manageable

### Git Workflow Essentials

**Branch Strategy:**
- Consider using a **dev/main branch strategy** for projects with production releases
- See `ClaudeUsage/git_workflow.md` for details on when and how to implement
- Keep development work in `dev`, merge to `main` when stable
- This is optional - simple projects can use a single branch

**After completing major changes, you MUST:**
1. Check git status: `git status`
2. Review recent commits for style: `git log --oneline -5`
3. Stage changes: `git add .`
4. Commit with proper message format (see below)

**Commit Message Format:**
```
[Action] [Brief description]

- [Specific change 1 with technical detail]
- [Specific change 2 with technical detail]
- [Additional implementation details]

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Action Verbs**: Add, Update, Fix, Refactor, Remove, Enhance

---

## When to Read Specific Guides

**Read the full guide in `ClaudeUsage/` when you encounter these situations:**

### Secrets & API Keys
- **When managing API keys or secrets** → Read `ClaudeUsage/secrets_management.md`
- **Before implementing secrets loading** → Read `ClaudeUsage/secrets_management.md`

### Package Management
- **When using UV package manager** → Read `ClaudeUsage/uv_usage.md`
- **Before creating pyproject.toml** → Read `ClaudeUsage/uv_usage.md`
- **When managing Python dependencies** → Read `ClaudeUsage/uv_usage.md`

### Version Control
- **Before making a git commit** → Read `ClaudeUsage/git_commit_guide.md`
- **When initializing a new repo** → Read `ClaudeUsage/git_commit_guide.md`
- **For git workflow details** → Read `ClaudeUsage/git_commit_guide.md`

### Search & Research
- **When searching across 20+ files** → Read `ClaudeUsage/house_agents.md`
- **When finding patterns in codebase** → Read `ClaudeUsage/house_agents.md`
- **When locating TODOs/FIXMEs** → Read `ClaudeUsage/house_agents.md`

### Testing
- **Before writing tests** → Read `ClaudeUsage/testing_strategies.md`
- **When implementing test coverage** → Read `ClaudeUsage/testing_strategies.md`
- **For test organization** → Read `ClaudeUsage/testing_strategies.md`


### Code Quality
- **When refactoring code** → Read `ClaudeUsage/code_style_guide.md`
- **Before major code changes** → Read `ClaudeUsage/code_style_guide.md`
- **For style guidelines** → Read `ClaudeUsage/code_style_guide.md`

### Project Setup
- **When starting a new project** → Read `ClaudeUsage/project_setup.md`
- **For directory structure** → Read `ClaudeUsage/project_setup.md`
- **Setting up CI/CD** → Read `ClaudeUsage/project_setup.md`

---

## Quick Reference

### Security Basics
- Store API keys in `secrets.json` (NEVER commit)
- Add `secrets.json` to `.gitignore` immediately
- Provide `secrets_template.json` for setup
- Use environment variables as fallbacks


### House Agents Quick Trigger
**When searching 20+ files**, use house-research for:
- Finding patterns across codebase
- Searching TODO/FIXME comments
- Locating API endpoints or functions
- Documentation searches

---

## Code Style Guidelines

### Function & Variable Naming
- Use meaningful, descriptive names
- Keep functions small and focused on single responsibilities
- Add docstrings to functions and classes

### Error Handling
- Use try/except blocks gracefully
- Provide helpful error messages
- Never let errors fail silently

### File Organization
- Group related functionality into modules
- Use consistent import ordering:
  1. Standard library
  2. Third-party packages
  3. Local imports
- Keep configuration separate from logic

---

## Communication Style
- Be concise but thorough
- Explain reasoning for significant decisions
- Ask for clarification when requirements are ambiguous
- Proactively suggest improvements when appropriate

---

## Complete Guide Index
For all detailed guides, workflows, and examples, see:
**`ClaudeUsage/README.md`** - Master index of all documentation

---

*Last updated: 2025-10-19*
*Model: Claude Sonnet 4.5*

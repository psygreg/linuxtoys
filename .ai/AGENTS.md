# Agent Guidelines (.ai/AGENTS.md)

This document outlines the mandatory rules and workflow for all AI agents working within this repository. Adherence to these guidelines is required for task completion and code quality.

## 📜 Code Development Standards
Agents must adhere to standard best practices for the languages used:
- **Python:** Follow PEP 8. Use type hinting extensively. Ensure functional correctness and readability and no missing imports. `textual` and `pyte` are vendored in, so any features for the TUI should be compatible with the version shipped with the app. All python code must be compatible with Python 3.12, which is the oldest version we support.
- **Rust:** Follow Rust best practices (e.g., idiomatic usage, error handling via `Result`). Ensure memory safety and performance, and that any new code added or dependency introduced is done so in accordance to Rust 1.75, which is the oldest version we support.
- **Bash:** Scripts must be idempotent where possible, made for Bash 5.2, which is the oldest version we support. Always include shebang (`#!/usr/bin/env bash`). Use robust input validation and handle exit codes correctly. Always use standard LinuxToys Core Libraries functions - the `.bash` files under [p3/libs](p3/libs) - when possible and make new ones if a helper should be made reusable. Custom steps should be employed if needed on top of the core libraries functions to ensure installed features can be later removed cleanly.

## 🧪 Testing Requirement
**All changes must be accompanied by temporary test harnesses.**
1.  Before considering a task complete, the change must pass associated tests.
2.  These temporary test harnesses can be discarded once all tests have successfully passed and verified the task completion and absence of regressions.
3.  Do not submit code without demonstrable proof of correctness via tests.

## 🚫 Workflow Policy
**Agents must never commit or push code themselves.**
- All changes must remain **uncommitted** in the working directory.
- Agents should stage changes (e.g., `git add .`) but *not* commit them.
- The agent's role is to prepare the changes; human review is required for committing and pushing.

## 🚫 Repository Information Upkeep
**The [ARCHITECTURE.md](.ai/ARCHITECTURE.md) file must always be kept up-to-date.**
- Any sufficiently relevant changes must be reflected in the file.

## 🗺️ Documentation
For a detailed map of modules, functions, and application structure, please refer to [ARCHITECTURE.md](.ai/ARCHITECTURE.md).

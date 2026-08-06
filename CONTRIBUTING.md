<!-- generated-by: gsd-doc-writer -->
# Contributing to Spoilerless

Thank you for your interest in contributing to Spoilerless! This document provides guidelines and instructions for submitting contributions to the project.

## Code of Conduct
Please ensure that all community interactions remain respectful, inclusive, and constructive. While there is no separate `CODE_OF_CONDUCT.md` file in the repository root, all contributors are expected to uphold standard open-source community standards.

## Issue Reporting
Before opening a new issue, search existing issues to avoid duplicates. When reporting a bug or requesting a feature:
- Use a clear and descriptive title.
- Provide a detailed description of the issue or proposed enhancement.
- Include step-by-step reproduction instructions (for bug reports).
- Include expected vs. actual behavior.
- Include relevant error logs or command output where applicable.

## Development Setup
For full environment setup details, see [README.md](README.md), [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), and [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

Quick setup summary:
- **Backend (Python 3.13)**: Managed with `uv`.
  - Install dependencies: `uv sync`
  - Seed graph database: `uv run --project spoilerless python -m spoilerless.app.graph.setup`
- **Database (Neo4j)**:
  - Start local Neo4j container: `docker compose up -d neo4j`
  - Set local environment variables before running tests: `source scripts/env-local.sh`
- **Frontend (Node.js 24 / React / TypeScript)**:
  - Navigate to frontend: `cd frontend`
  - Install dependencies: `npm ci`
  - Start dev server: `npm run dev`

## Coding Standards
- **Backend (Python)**:
  - Ensure compatibility with Python >= 3.13.
  - Follow standard Python style guidelines.
  - Write unit and integration tests under `spoilerless/tests`.
  - Ensure `uv run pytest` passes cleanly.
  - Ensure test runs leave zero database pollution (no remaining `series_scratch*` nodes or `candidate` origin rows).
- **Frontend (TypeScript / React)**:
  - Code using TypeScript and React 19.
  - Ensure code passes ESLint: `npm run lint`
  - Ensure unit tests pass: `npm run test`
  - Ensure TypeScript type checks and Vite build pass: `npm run build`

## Pull Request Guidelines
1. Fork the repository and create your feature branch from `main` (`git checkout -b feature/my-feature`).
2. Implement your changes, adding tests for new functionality where applicable.
3. Test your changes locally:
   - Backend: Run `uv run pytest` with local Neo4j configured (`source scripts/env-local.sh`).
   - Frontend: Run `npm run lint`, `npm run test`, and `npm run build` in `frontend/`.
4. Verify that CI workflows will pass. The GitHub Actions pipeline in [.github/workflows/ci.yml](.github/workflows/ci.yml) checks:
   - Backend: dependencies sync, database setup, `pytest` execution, and DB-pollution assertions.
   - Frontend: `npm ci`, `npm run build`, `npm run lint`, and `npm audit --audit-level=high`.
5. Open a Pull Request against the `main` branch with a concise title and clear summary of changes.

We appreciate your contributions!

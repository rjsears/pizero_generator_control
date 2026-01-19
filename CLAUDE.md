# Claude Code Project Instructions

## Git Workflow

- **Always create a new feature branch for each piece of work** - keep features separate for cleaner PRs
- Branch naming convention: `feature/<feature-name>` or `fix/<fix-name>`
- Create branches from `main` unless otherwise specified
- Do not mix unrelated changes in the same branch/PR
- **NEVER merge branches** - only create PRs and let the user merge them

## Project Structure

- Backend: `genmaster/backend/` - FastAPI with SQLAlchemy async
- Frontend: `genmaster/frontend/` - Vue 3 with Composition API
- Database: PostgreSQL with Alembic migrations
- Deployment: Docker containers

## Coding Conventions

- Backend uses Python type hints and Pydantic schemas
- Frontend uses JavaScript (not TypeScript), Vue 3 `<script setup>` syntax
- Follow existing patterns in the codebase for new files

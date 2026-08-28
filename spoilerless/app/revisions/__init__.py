"""Named submodules: repository.py (queries + RevisionRepository), service.py (revert business flow + domain exceptions)."""

from spoilerless.app.revisions.repository import RevisionRepository
from spoilerless.app.revisions.service import RevisionService

__all__ = ["RevisionRepository", "RevisionService"]

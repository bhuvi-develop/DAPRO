"""Import every model so Alembic and the ORM registry see the full schema."""
from app.models.base import RLS_TABLES, Base  # noqa: F401
from app.models.engagement import *  # noqa: F401,F403
from app.models.iam import *  # noqa: F401,F403
from app.models.loans import *  # noqa: F401,F403
from app.models.ops import *  # noqa: F401,F403
from app.models.platform import *  # noqa: F401,F403
from app.models.students import *  # noqa: F401,F403

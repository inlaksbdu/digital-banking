from typing import Any, Dict, TypeVar

from django.db import models
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig, ensure_config

ModelType = TypeVar("ModelType", bound=models.Model)


class GenericBaseTool(BaseTool):
    def get_user(self, config: RunnableConfig | None = None) -> Dict[str, Any]:
        configurable = ensure_config(config).get("configurable", {})
        user = configurable.get("user")
        if not user:
            raise ValueError("User not found in config")
        return user

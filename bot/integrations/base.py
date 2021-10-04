from __future__ import annotations

from typing import Type, Dict


class Integration:
    """
    Integrations provide third-party APIs to command implementations
    """

    name: str = None
    registry: Dict[str, Type[Integration]] = {}

    def __init__(self, **kwargs):
        pass

    def __init_subclass__(cls):
        """
        Registers imported integrations into a registry stored within the base class.
        :return:
        """
        assert cls.name is not None, f"{cls.__name__}.name unset"
        exists = cls.registry.get(cls.name)
        assert exists is None, f"{cls.name} already registered: {exists.__name__}"
        cls.registry[cls.name] = cls

    @classmethod
    def get_integration(cls, name: str) -> Type[Integration]:
        """
        Fetches an integration by key from `Integration.registry`.
        :param name:
        :return:
        """
        exists = cls.registry.get(name)
        assert exists, f"integration not found: {name}"
        return exists

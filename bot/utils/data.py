from __future__ import annotations

import json
from typing import Set

import pydantic

from bot.utils.hashing import hashify


Field = pydantic.Field


class Data(pydantic.BaseModel):
    """
    Utility data class that enables marking fields for hashing + persistence.

    class Model(Data):
        included_in_hash = Field(hash=True)
        included_in_persistence = Field(persist=True)

    m = Model()
    other = Model()
    m.hash()
    m.persist_str()
    m.update(other)
    m.update_from_persist_str(other.persist_str())
    """

    def persist_field_names(self) -> Set[str]:
        """
        Gets a list of all field names annotated with `persist=True`
        :return:
        """
        persist_field_names = set()
        for name, field in self.__fields__.items():
            field_extra = field.field_info.extra
            include_field = field_extra.get("persist", False)
            if not include_field:
                continue
            persist_field_names.add(name)
        return persist_field_names

    def hash_field_names(self) -> Set[str]:
        """
        Gets a list of all field names annotated with `hash=True`
        :return:
        """
        hash_field_names = set()
        for name, field in self.__fields__.items():
            field_extra = field.field_info.extra
            include_field = field_extra.get("hash", False)
            if not include_field:
                continue
            hash_field_names.add(name)
        return hash_field_names

    def update_from_persist_str(self, other_persist_str: str):
        """
        Convenience method to update self with data found in `other_persist_str`.
        `other_persist_str` is assumed to be the result of a former call to `self.other_persist_str()`.
        :param other_persist_str:
        :return:
        """
        other = self.dict()
        other.update(json.loads(other_persist_str))
        other = self.parse_obj(other)
        self.update(other)

    def update(self, other: Data):
        """
        Updates `self` with all fields annotated with `persist=True` from `other`.
        :param other:
        :return:
        """
        for field_name in self.persist_field_names():
            setattr(self, field_name, getattr(other, field_name))

    def persist_str(self) -> str:
        """
        Generates a text blob of all fields annotated with `persist=True` from `self`.
        :return:
        """
        return self.json(include=self.persist_field_names(), sort_keys=True)

    def hash(self) -> str:
        """
        Generates a hash string of all fields annotated with `hash=True` from `self`.
        :return:
        """
        hash_dict = self.dict(include=self.hash_field_names())
        return hashify(hash_dict)

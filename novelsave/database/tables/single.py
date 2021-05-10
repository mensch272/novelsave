from typing import List

from .template import Table
from ..template import Database


class SingleClassTable(Table):
    def __init__(self, db: Database, table: str, cls, fields: List[str]):
        super(SingleClassTable, self).__init__(db, table)

        self.cls = cls
        self.fields = fields

    def set(self, values):
        self.data = {field: getattr(values, field) for field in self.fields}

    def parse(self):
        return self.cls(**{key: value for key, value in self.data.items() if key in self.fields})

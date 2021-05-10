from .template import Database
from .tables import KeyValueTable, SingleClassTable, MultiClassExternalTable, MultiClassDecoupledTable, \
    SetTable
from ..models import Novel, Chapter


class NovelData(Database):
    def __init__(self, directory, should_create=True, load_chapters=True):
        super(NovelData, self).__init__(directory, should_create)

        self.novel = SingleClassTable(self, 'novel', Novel,
                                      ['title', 'author', 'synopsis', 'thumbnail', 'lang', 'meta_source', 'url'])
        self.metadata = SetTable(self.db, 'metadata', field1='name', field2='value')
        self.pending = MultiClassDecoupledTable(self.db, self.path.parent, 'pending', Chapter,
                                                ['index', 'title', 'volume', 'url'], 'url')
        self.chapters = MultiClassExternalTable(
            self.db, self.path.parent, 'chapters',
            Chapter, ['index', 'title', 'paragraphs', 'volume', 'url'], 'url',
            naming_scheme=lambda c: str(c.index).zfill(4),
            load=load_chapters
        )
        self.misc = KeyValueTable(self.db, 'misc')

    def close(self):
        self.pending.decoupled_db.close()
        self.db.close()

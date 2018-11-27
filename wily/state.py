"""
For managing the state of the wily process.

Contains a lazy revision, index and process state model.
"""
from collections import OrderedDict
from dataclasses import asdict
import wily.cache as cache
from wily import logger
from wily.archivers import Revision, resolve_archiver


class Index(object):
    """The index of the wily cache."""
    operators = None

    def __init__(self, config, archiver):
        """
        Instantiate a new index.

        :param config: The wily config.
        :type  config: :class:`wily.config.WilyConfig`

        :param archiver: The archiver.
        :type  archiver: :class:`wily.archivers.Archiver`
        """
        self.config = config
        self.archiver = archiver
        self.data = (
            cache.get_index(config, archiver.name)
            if cache.has_index(config, archiver.name)
            else []
        )
        # If only Python supported Ordered Dict comprehensions :-(
        self._revisions = OrderedDict()
        for d in self.data:
            if not self.operators:
                self.operators = d['operators']
            self.add(Revision(key=d['revision'], author_name=d['author_name'], author_email=d['author_email'], date=d['date'], message=d['message']))

    def __len__(self):
        """Use length of revisions as len."""
        return len(self._revisions)

    @property
    def revisions(self):
        """
        List of all the revisions.

        :rtype: ``list`` of :class:`LazyRevision`
        """
        return list(self._revisions.values())

    @property
    def revision_keys(self):
        """
        List of all the revision indexes.

        :rtype: ``list`` of ``str``
        """
        return list(self._revisions.keys())

    def __contains__(self, item):
        """
        Check if index contains `item`.

        :param item: The item to search for
        :type  item: ``str``, :class:`Revision` or :class:`LazyRevision`

        :return: ``True`` for contains, ``False`` for not.
        """
        if isinstance(item, Revision):
            return item.key in self._revisions
        elif isinstance(item, str):
            return item in self._revisions
        else:
            raise TypeError("Invalid type for __contains__ in Index.")

    def __getitem__(self, index):
        """Get the revision for a specific index."""
        return self._revisions[index]

    def add(self, revision):
        """
        Add a revision to the index.

        :param revision: The revision.
        :type  revision: :class:`Revision` or :class:`LazyRevision`
        """
        self._revisions[revision.key] = revision

    def save(self):
        """Save the index data back to the wily cache."""
        data = [asdict(i) for i in self._revisions.values()]
        cache.store_index(self.config, self.archiver, data)


class State(object):
    """
    The wily process state.

    Includes indexes for each archiver.
    """

    def __init__(self, config, archiver=None):
        """
        Instantiate a new process state.

        :param config: The wily configuration.
        :type  config: :class:`WilyConfig`

        :param archiver: The archiver (optional).
        :type  archiver: :class:`wily.archivers.Archiver`
        """
        if archiver:
            self.archivers = [archiver.name]
        else:
            self.archivers = cache.list_archivers(config)
        self.config = config
        self.index = {}
        for archiver in self.archivers:
            self.index[archiver] = Index(self.config, resolve_archiver(archiver))
        self.default_archiver = self.archivers[0]

    def ensure_exists(self):
        """Ensure that cache directory exists."""
        if not cache.exists(self.config):
            logger.debug("Wily cache not found, creating.")
            cache.create(self.config)
            logger.debug("Created wily cache")

from datetime import datetime, date
import pendulum
import singer
from singer import bookmarks as bks_
from singer import metadata
from .http import get_client


class Context(object):
    """Represents a collection of global objects necessary for performing
    discovery or for running syncs. Notably, it contains

    - config  - The JSON structure from the config.json argument
    - state   - The mutable state dict that is shared among streams
    - client  - An HTTP client object for interacting with Listrak
    - catalog - A singer.catalog.Catalog. Note this will be None during
                discovery.
    - cache   - A place for streams to store data so it can be shared between
                streams.
    """
    def __init__(self, config, state):
        self.config = config
        self.state = state
        self.client = get_client(config)
        self._catalog = None
        self.selected_stream_ids = None
        self.cache = {}
        self.now = datetime.utcnow()
        self.end_date = config.get("end_date", self.now)

    @property
    def catalog(self):
        return self._catalog

    @catalog.setter
    def catalog(self, catalog):
        self._catalog = catalog
        self.selected_stream_ids = set(
            [s.tap_stream_id for s in catalog.streams
             if s.is_selected() or metadata.get(metadata.to_map(s.metadata),
                                                (),
                                                'inclusion') == 'automatic']
        )

    def get_bookmark(self, path):
        return bks_.get_bookmark(self.state, *path)

    def set_bookmark(self, path, val):
        if isinstance(val, date):
            val = val.isoformat()
        bks_.write_bookmark(self.state, path[0], path[1], val)

    def get_offset(self, path):
        off = bks_.get_offset(self.state, path[0])
        return (off or {}).get(path[1])

    def set_offset(self, path, val):
        bks_.set_offset(self.state, path[0], path[1], val)

    def clear_offsets(self, tap_stream_id):
        bks_.clear_offset(self.state, tap_stream_id)

    def update_start_date_bookmark(self, path):
        val = self.get_bookmark(path)
        if not val:
            val = self.config["start_date"]
            self.set_bookmark(path, val)
        return pendulum.parse(val)

    def write_state(self):
        singer.write_state(self.state)

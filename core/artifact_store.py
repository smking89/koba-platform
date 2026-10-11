"""Artifact Store (master spec's artifact_store/versioning/cache,
extending section 4's Artifact Graph) — a real content-addressed blob
store built directly on core.artifact_graph.hash_file/hash_data, which
already do the hard part (computing hashes, comparing them in
has_changed()). This module adds what those don't: an actual place
artifact bytes live, keyed by their own hash, plus a real cache lookup
keyed by (processor, input_hash, params) so a repeat real tool call with
byte-identical inputs and identical parameters can be skipped entirely
instead of silently re-running an expensive Blender subprocess for an
output that's already known.

"Versioning" here is a direct consequence of content-addressing, not a
separate mechanism: every distinct version of a file gets its own
permanent slot keyed by its own hash, and identical content is never
duplicated or overwritten — put() of the same bytes twice is a no-op the
second time.

Scope honesty: one project-local, flat content-addressed directory, no
garbage collection, no remote/shared store across projects, no
compression. The master spec's full artifact_store is a shared, GC'd,
possibly-remote object store; this is the bounded, real, single-project
version of it — exactly how big a store this codebase currently has a
genuine use for (see repair/repair_manager.py's cache integration).
"""
import datetime
import json
import os
import shutil

from core.artifact_graph import hash_file, hash_data

STORE_DIRNAME = "artifact_store"
OBJECTS_DIRNAME = "objects"
CACHE_INDEX_FILENAME = "cache_index.json"


def _store_dir(proj_dir):
    return os.path.join(proj_dir, STORE_DIRNAME)


def _objects_dir(proj_dir):
    return os.path.join(_store_dir(proj_dir), OBJECTS_DIRNAME)


def _object_path(proj_dir, content_hash):
    # Two-level fan-out (same scheme git uses) so a single directory
    # never ends up holding thousands of entries for a long-lived
    # project.
    return os.path.join(_objects_dir(proj_dir), content_hash[:2], content_hash[2:])


def put(proj_dir, src_path):
    """Stores a real file's bytes under the store, keyed by their own
    sha256 — the SAME hash function core.artifact_graph already uses for
    an artifact's output_hash, so an artifact's output_hash IS its
    object key; nothing new to compute. Returns the content hash.
    Idempotent: storing byte-identical content twice is a genuine no-op
    the second time (the object already exists at that path)."""
    content_hash = hash_file(src_path)
    dest = _object_path(proj_dir, content_hash)
    if not os.path.isfile(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(src_path, dest)
    return content_hash


def get(proj_dir, content_hash):
    """Returns the real path to a stored object's bytes, or None if this
    store doesn't have it. Never fabricates a hit."""
    path = _object_path(proj_dir, content_hash)
    return path if os.path.isfile(path) else None


def has(proj_dir, content_hash):
    return get(proj_dir, content_hash) is not None


def _load_cache_index(proj_dir):
    path = os.path.join(_store_dir(proj_dir), CACHE_INDEX_FILENAME)
    if not os.path.isfile(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def _save_cache_index(proj_dir, index):
    os.makedirs(_store_dir(proj_dir), exist_ok=True)
    path = os.path.join(_store_dir(proj_dir), CACHE_INDEX_FILENAME)
    with open(path, "w") as f:
        json.dump(index, f, indent=2)


def cache_key(processor, input_hash, params):
    """A real, deterministic key: which processor, which exact input
    bytes, which exact parameters — never a guess at equivalence, only
    an exact match. `params` must be JSON-serializable (the same
    constraint orchestrator.job.create_job already places on Job args)."""
    return hash_data({"processor": processor, "input_hash": input_hash, "params": params})


def cache_lookup(proj_dir, processor, input_hash, params):
    """Returns the stored output's real file path if this EXACT
    (processor, input_hash, params) combination has been computed
    before AND its bytes are still physically present in the store —
    never a stale hit; a missing object (e.g. the project dir was
    partially cleaned up by hand) is treated as an honest miss, not a
    hit it can't back up. Returns None on any miss."""
    key = cache_key(processor, input_hash, params)
    index = _load_cache_index(proj_dir)
    entry = index.get(key)
    if entry is None:
        return None
    return get(proj_dir, entry["output_hash"])


def list_cache_entries(proj_dir):
    """Every recorded (processor, input_hash, params) -> output_hash
    mapping, for inspection (the `cache` CLI command) — not the cache
    key itself (an opaque hash), but what's actually known about each
    entry: whether its object is still physically present or has been
    evicted/lost."""
    index = _load_cache_index(proj_dir)
    entries = []
    for key, entry in index.items():
        entries.append({
            "key": key, "output_hash": entry["output_hash"], "cached_at": entry["cached_at"],
            "object_present": has(proj_dir, entry["output_hash"]),
        })
    return sorted(entries, key=lambda e: e["cached_at"])


def store_stats(proj_dir):
    """Real counts from the filesystem — object count and total bytes
    actually stored, plus how many cache-index entries exist (which can
    exceed the object count if several entries point at the same
    deduplicated bytes)."""
    objects_dir = _objects_dir(proj_dir)
    object_count = 0
    total_bytes = 0
    if os.path.isdir(objects_dir):
        for root, _dirs, files in os.walk(objects_dir):
            for fname in files:
                object_count += 1
                total_bytes += os.path.getsize(os.path.join(root, fname))
    return {
        "object_count": object_count, "total_bytes": total_bytes,
        "cache_entries": len(_load_cache_index(proj_dir)),
    }


def cache_store(proj_dir, processor, input_hash, params, output_path):
    """Stores output_path's bytes in the content-addressed store AND
    records the (processor, input_hash, params) -> output_hash mapping,
    so a future cache_lookup() with identical inputs can skip
    recomputation. Returns the output's content hash."""
    output_hash = put(proj_dir, output_path)
    key = cache_key(processor, input_hash, params)
    index = _load_cache_index(proj_dir)
    index[key] = {
        "output_hash": output_hash,
        "cached_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    _save_cache_index(proj_dir, index)
    return output_hash

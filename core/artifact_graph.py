"""The Artifact Graph — KOBA's system of record for production output
(master spec section 4). Every meaningful thing a processor produces
becomes a node here, not just a file dropped in a directory: what
produced it, what it depends on, whether it's still valid, and how to
tell if it needs rebuilding.

This is deliberately NOT the same thing as core.manifest's project.json
— that's the human-readable product-level summary (section 12's Product
Manifest: Identity/Assets/Exports/Errors). This module is the fine-
grained dependency graph everything else (incremental rebuilds, the
repair loop, the compiler) needs to exist before it can be built for
real, per ARCHITECTURE_ASSESSMENT.md's Phase A recommendation.

One graph per project, persisted as artifact_graph.json alongside
project.json. Plain JSON on disk — no database — consistent with the
rest of this codebase's dependency-free approach.
"""
import datetime
import hashlib
import json
import os
import uuid

GRAPH_FILENAME = "artifact_graph.json"

# Matches the vocabulary in master spec section 11 (validators decide
# PASS/FAIL/BLOCKED/UNSUPPORTED) plus two practical additions this graph
# itself needs: PENDING (not validated yet) and INVALID (was valid, but a
# dependency changed — needs revalidation/rebuild before it can be trusted).
PENDING = "PENDING"
PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
UNSUPPORTED = "UNSUPPORTED"
INVALID = "INVALID"


def hash_file(path):
    """sha256 of a file's actual bytes — the InputHash/OutputHash for any
    artifact backed by a real file (a .blend, a .png, an .svg, ...)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_data(obj):
    """sha256 of a canonical JSON encoding — for artifacts not backed by
    one file (e.g. a set of build parameters, or a directory of outputs
    hashed by listing them)."""
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ArtifactGraph:
    def __init__(self):
        self.artifacts = {}  # {artifact_id: artifact_dict}

    # --- construction -----------------------------------------------------

    def add_artifact(self, artifact_type, processor, product_id=None, version_id=None,
                      job_id=None, stage_id=None, parent_artifacts=None, dependencies=None,
                      processor_version=None, input_hash=None, output_path=None,
                      storage_location=None, metadata=None, validation_status=PENDING):
        """Registers a new artifact node. output_path, if given, is hashed
        automatically for OutputHash (the common case: a processor wrote a
        real file). parent_artifacts/dependencies are lists of artifact IDs
        that must already exist in this graph — raises if they don't,
        since a dangling edge would silently break lineage traversal."""
        parent_artifacts = list(parent_artifacts or [])
        dependencies = list(dependencies or [])
        for pid in parent_artifacts + dependencies:
            if pid not in self.artifacts:
                raise ValueError(f"Unknown parent/dependency artifact id: {pid}")

        output_hash = hash_file(output_path) if output_path and os.path.isfile(output_path) else None

        artifact_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.artifacts[artifact_id] = {
            "artifact_id": artifact_id,
            "product_id": product_id,
            "version_id": version_id,
            "job_id": job_id,
            "stage_id": stage_id,
            "parent_artifacts": parent_artifacts,
            "dependencies": dependencies,
            "artifact_type": artifact_type,
            "processor": processor,
            "processor_version": processor_version,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "validation_status": validation_status,
            "created_at": now,
            "storage_location": storage_location or output_path,
            "metadata": metadata or {},
        }
        return artifact_id

    def get(self, artifact_id):
        return self.artifacts.get(artifact_id)

    def set_validation_status(self, artifact_id, status):
        if artifact_id not in self.artifacts:
            raise ValueError(f"Unknown artifact id: {artifact_id}")
        self.artifacts[artifact_id]["validation_status"] = status

    # --- traversal ----------------------------------------------------------

    def _edges_of(self, artifact_id):
        a = self.get(artifact_id)
        if a is None:
            return []
        return list(a["parent_artifacts"]) + list(a["dependencies"])

    def parents_of(self, artifact_id):
        """Direct parents/dependencies, resolved to artifact dicts."""
        return [self.artifacts[pid] for pid in self._edges_of(artifact_id) if pid in self.artifacts]

    def children_of(self, artifact_id):
        """Direct children — every artifact that lists artifact_id as a
        parent or dependency. O(n) over the graph; fine at this scale
        (single-project graphs), not meant for a huge shared graph."""
        return [a for a in self.artifacts.values() if artifact_id in self._edges_of(a["artifact_id"])]

    def lineage(self, artifact_id):
        """Full ancestor chain (every artifact this one transitively
        depends on), deduplicated, order not guaranteed."""
        seen = set()
        stack = [artifact_id]
        result = []
        while stack:
            current = stack.pop()
            for parent in self._edges_of(current):
                if parent not in seen:
                    seen.add(parent)
                    result.append(self.artifacts[parent])
                    stack.append(parent)
        return result

    def find_affected(self, artifact_id):
        """Every artifact that transitively depends on artifact_id — i.e.
        what would need rebuilding if artifact_id changes (master spec
        section 5's incremental-rebuild example: a changed material
        affects its validation + affected prefabs + affected package, but
        must NOT touch unrelated NPC logic/events/loot unless the graph
        actually says they depend on it)."""
        seen = set()
        stack = [artifact_id]
        result = []
        while stack:
            current = stack.pop()
            for child in self.children_of(current):
                cid = child["artifact_id"]
                if cid not in seen:
                    seen.add(cid)
                    result.append(child)
                    stack.append(cid)
        return result

    # --- change detection / invalidation ------------------------------------

    def has_changed(self, artifact_id, new_input_hash):
        """Compare a freshly-computed input hash against what's stored —
        the basis for "should this artifact be rebuilt at all" (section 5)."""
        a = self.get(artifact_id)
        if a is None:
            raise ValueError(f"Unknown artifact id: {artifact_id}")
        return a["input_hash"] != new_input_hash

    def invalidate(self, artifact_id, cascade=True):
        """Marks an artifact INVALID, and — since it changed — every
        artifact that transitively depends on it, per section 5. Returns
        the list of artifact_ids that got invalidated (artifact_id itself
        plus, if cascade, its full find_affected() set) so a caller can
        report exactly what needs rebuilding."""
        if artifact_id not in self.artifacts:
            raise ValueError(f"Unknown artifact id: {artifact_id}")
        invalidated = [artifact_id]
        self.set_validation_status(artifact_id, INVALID)
        if cascade:
            for a in self.find_affected(artifact_id):
                self.set_validation_status(a["artifact_id"], INVALID)
                invalidated.append(a["artifact_id"])
        return invalidated

    # --- comparison ----------------------------------------------------------

    def diff(self, artifact_id_a, artifact_id_b):
        """Field-by-field comparison of two artifacts — e.g. two versions
        of the same logical asset. Returns {field: (value_a, value_b)} for
        every field that differs."""
        a = self.get(artifact_id_a)
        b = self.get(artifact_id_b)
        if a is None or b is None:
            raise ValueError("Both artifact ids must exist to diff")
        differences = {}
        for key in set(a) | set(b):
            if a.get(key) != b.get(key):
                differences[key] = (a.get(key), b.get(key))
        return differences

    # --- persistence ----------------------------------------------------------

    def to_dict(self):
        return {"artifacts": self.artifacts}

    @classmethod
    def from_dict(cls, data):
        graph = cls()
        graph.artifacts = data.get("artifacts", {})
        return graph


def find_by_path(graph, path):
    """The artifact whose storage_location matches `path`, if any — used
    to avoid creating a duplicate source-artifact node every time the CLI
    runs against the same file."""
    abs_path = os.path.abspath(path)
    for artifact in graph.artifacts.values():
        loc = artifact.get("storage_location")
        if loc and os.path.abspath(loc) == abs_path:
            return artifact
    return None


def get_or_create_source_artifact(graph, path, artifact_type):
    """Finds the existing artifact for `path`, or registers a new
    zero-dependency source node for it (e.g. a .blend a user dropped into
    a project's blender/ directory outside this pipeline — it still needs
    an artifact node to be a valid parent for anything derived from it)."""
    existing = find_by_path(graph, path)
    if existing is not None:
        return existing["artifact_id"]
    return graph.add_artifact(
        artifact_type=artifact_type, processor="external", input_hash=hash_file(path),
        output_path=path, validation_status=PENDING,
    )


def new_graph():
    return ArtifactGraph()


def load_graph(project_dir):
    path = os.path.join(project_dir, GRAPH_FILENAME)
    if not os.path.isfile(path):
        return new_graph()
    with open(path, "r") as f:
        return ArtifactGraph.from_dict(json.load(f))


def save_graph(project_dir, graph):
    path = os.path.join(project_dir, GRAPH_FILENAME)
    with open(path, "w") as f:
        json.dump(graph.to_dict(), f, indent=2)
    return path

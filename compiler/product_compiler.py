"""Product Compiler (master spec's `compiler/product_compiler`).

Scope honesty: this is the ONE real compiler, not the spec's full
product_compiler + dependency_compiler + runtime_compiler + asset_compiler
+ manifest_compiler set — built the same way blender_agent proved the
one-agent pattern before 16 more were built. It does one real thing:
collect the currently-PASSing artifacts for a project's registered
product type into a CompiledProduct descriptor, ready for
packaging/package_builder.py to actually write to disk.

Rule 2 (AI/tooling is not the validation authority) applies here exactly
as everywhere else: compile_product() NEVER re-validates or re-decides
PASS/FAIL. It only reads what the artifact graph's validation_status
already says, recorded by a real validator at some earlier point
(validate_blend, texture_validator, audio_validator, ...). An artifact
that's PENDING, FAIL, or INVALID is excluded from the release, not
"fixed" or guessed at.
"""
import datetime

from core.artifact_graph import load_graph, PASS as ART_PASS
from core.manifest import load_manifest
from products.product_types import get as get_product_type, UnknownProductType


class CompilerError(Exception):
    pass


def compile_product(proj_dir):
    """Returns a CompiledProduct dict — not yet written to disk, that's
    packaging/package_builder.build_package()'s job. Raises CompilerError
    (never silently produces an empty/partial release) if the project has
    no registered product type, or has no currently-PASSing artifacts to
    release."""
    manifest = load_manifest(proj_dir)
    product_type = manifest.get("product_type")
    if not product_type:
        raise CompilerError(
            "this project has no registered product type — run `register-product` first "
            "(see products/product_types.py)"
        )

    try:
        schema = get_product_type(product_type)
    except UnknownProductType as e:
        raise CompilerError(str(e)) from e

    graph = load_graph(proj_dir)
    release_artifacts = [
        a for a in graph.artifacts.values()
        if a["validation_status"] == ART_PASS
    ]
    if not release_artifacts:
        raise CompilerError(
            f"no artifacts with validation_status=PASS in this project's artifact graph — "
            f"nothing real to compile. Run validate/optimize/register-product first."
        )

    return {
        "product_type": product_type,
        "product_metadata": manifest.get("product_metadata", {}),
        "source_project": manifest["name"],
        "compiled_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "required_validators": schema.required_validators,
        "artifacts": [
            {
                "artifact_id": a["artifact_id"],
                "artifact_type": a["artifact_type"],
                "output_path": a["storage_location"],
                "output_hash": a["output_hash"],
                "validation_status": a["validation_status"],
            }
            for a in sorted(release_artifacts, key=lambda a: a["created_at"])
        ],
    }

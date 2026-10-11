from tests.test1_crate import build_crate

asset = build_crate(interactive=True)
print("Live asset created:", asset.summary())

"""Shared argv reconstruction — rebuilds a CLI invocation's argv from a
plain {dest_name: value} args dict, the same shape orchestrator.job.py
persists per-job and orchestrator.pipeline_manager.py persists per-stage.
Used by cli.main's `resume` command (re-entering a single FAILED job) and
by pipeline_manager (executing each stage of a pipeline) — factored out
once a second real caller needed the exact same logic, not speculatively.
"""


def reconstruct_argv(command, args):
    """Relies on every cmd_* handler storing args under the same dest
    names argparse would use (see the create_job() calls throughout
    cli/main.py) — 'name' is always the positional project name, every
    other key becomes --key-with-dashes, booleans become bare flags."""
    argv = [command]
    name = args.get("name")
    if name is not None:
        argv.append(name)
    for key, value in args.items():
        if key == "name" or value is None:
            continue
        flag = "--" + key.replace("_", "-")
        if isinstance(value, bool):
            if value:
                argv.append(flag)
        else:
            argv.append(flag)
            argv.append(str(value))
    return argv

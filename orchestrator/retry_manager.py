"""Retry Manager (master spec section 25's checkpoint-based retry) — a
bounded wrapper around the existing checkpoint/resume mechanism
(orchestrator.job's persisted command+args, replayed by cli.main's
resume logic), not a new checkpoint format of its own. Every failed
attempt already leaves a real Job record (state FAILED, with its
original command+args) behind on disk — see orchestrator/job.py's
docstring; this module just calls that same resume logic repeatedly
against whatever is currently resumable, up to max_attempts, stopping
at the first success, and refuses to loop forever if nothing resumable
is left or a target job turns out not to actually be FAILED.
"""
import time

from orchestrator.job import find_resumable, get_job
from orchestrator.build_state import FAILED

DEFAULT_MAX_ATTEMPTS = 3


class RetryExhausted(Exception):
    pass


def retry_job(proj_dir, resume_once, job_id=None, max_attempts=DEFAULT_MAX_ATTEMPTS, backoff_seconds=0):
    """resume_once(job) -> exit_code is injected rather than imported
    from cli.main — cli.main is this project's entry point and already
    imports every orchestrator module it uses, so importing it back here
    would create an import cycle.

    Returns {"attempts": [{"attempt", "job_id", "exit_code"}, ...],
             "succeeded": bool}. Raises RetryExhausted immediately (zero
    attempts made) if there is nothing resumable to start from, or the
    named job_id isn't actually FAILED — same as resume's own refusal,
    never silently no-ops."""
    attempts = []
    next_job_id = job_id

    for attempt_num in range(1, max_attempts + 1):
        job = get_job(proj_dir, next_job_id) if next_job_id else find_resumable(proj_dir)
        if job is None:
            raise RetryExhausted(f"no resumable (FAILED) job found after {len(attempts)} attempt(s)")
        if job["state"] != FAILED:
            raise RetryExhausted(
                f"job {job['job_id']} is in state {job['state']}, not FAILED — nothing to retry"
            )

        exit_code = resume_once(job)
        attempts.append({"attempt": attempt_num, "job_id": job["job_id"], "exit_code": exit_code})

        if exit_code == 0:
            return {"attempts": attempts, "succeeded": True}

        # A failed replay's OWN command creates its own fresh FAILED job
        # (same as a single manual `resume`) — the next iteration must
        # pick THAT one up via find_resumable(), not retry the job we
        # just closed out (which is no longer FAILED).
        next_job_id = None
        if attempt_num < max_attempts and backoff_seconds:
            time.sleep(backoff_seconds)

    return {"attempts": attempts, "succeeded": False}

from dataclasses import dataclass

OVERDUE_MULTIPLIER = 2


@dataclass(frozen=True)
class ScheduledJob:
    name: str
    every_minutes: int
    cron: str
    purpose: str


SCHEDULE = (
    ScheduledJob("expire_requests", 15, "*/15 * * * *",
                 "Close requests nobody answered within 24 hours."),
    ScheduledJob("auto_confirm", 60, "5 * * * *",
                 "Confirm jobs the customer left unconfirmed for 72 hours."),
    ScheduledJob("reveal_reviews", 60, "10 * * * *",
                 "Publish reviews whose 14-day double-blind window closed."),
    ScheduledJob("recompute_all_trust", 1440, "0 3 * * *",
                 "Refresh every trust score so time decay keeps moving."),
    ScheduledJob("reconcile_earnings", 1440, "30 3 * * *",
                 "Check every ledger against its payments."),
    ScheduledJob("purge_otps", 10, "*/10 * * * *",
                 "Delete spent and expired verification codes."),
    ScheduledJob("purge_documents", 1440, "0 4 * * *",
                 "Delete verification files past their retention window."),
)

JOBS_BY_NAME = {job.name: job for job in SCHEDULE}


def get_job(name):
    return JOBS_BY_NAME[name]

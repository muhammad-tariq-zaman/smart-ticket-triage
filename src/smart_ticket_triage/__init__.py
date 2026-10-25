"""Smart Ticket Triage — classify, prioritise and SLA-track IT support tickets.

Rule-based and fully offline: no API key, no invented data. It reads a
CSV of tickets, classifies each one, assigns a priority from impact +
urgency, computes the SLA due time, and writes a triaged CSV + summary.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

CATEGORIES = {
    "account": ["password", "login", "locked out", "mfa", "otp", "access denied",
                "account", "reset", "sign in", "sign-in", "credentials"],
    "connectivity": ["wifi", "wi-fi", "internet", "vpn", "network", "dns",
                     "offline", "no connection", "lan", "ethernet", "router"],
    "device": ["laptop", "printer", "monitor", "keyboard", "mouse", "battery",
               "screen", "hardware", "blue screen", "crash", "slow"],
    "software": ["outlook", "teams", "excel", "word", "office", "m365",
                 "application", "software", "update", "install", "error"],
}

# SLA targets in hours, by priority (configurable, documented in README).
SLA_HOURS = {"P1": 4, "P2": 8, "P3": 24, "P4": 72}


def classify(text: str) -> str:
    """Return the best-matching category for a ticket description."""
    lowered = text.lower()
    scores = {}
    for category, keywords in CATEGORIES.items():
        scores[category] = sum(1 for kw in keywords if kw in lowered)
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "general"


def priority(impact: str, urgency: str) -> str:
    """Priority matrix: impact/urgency are 'high', 'medium' or 'low'."""
    impact = impact.strip().lower()
    urgency = urgency.strip().lower()
    if impact not in ("high", "medium", "low") or urgency not in ("high", "medium", "low"):
        raise ValueError("impact and urgency must be high, medium or low")
    if impact == "high" and urgency == "high":
        return "P1"
    if impact == "high" or urgency == "high":
        return "P2"
    if impact == "medium" or urgency == "medium":
        return "P3"
    return "P4"


def sla_due(created_at: str, prio: str) -> str:
    """SLA due time as ISO string, from a '%Y-%m-%d %H:%M' created time."""
    created = datetime.strptime(created_at, "%Y-%m-%d %H:%M")
    return (created + timedelta(hours=SLA_HOURS[prio])).isoformat(timespec="minutes")


@dataclass
class Ticket:
    id: str
    title: str
    description: str
    impact: str
    urgency: str
    created_at: str
    category: str = field(init=False)
    prio: str = field(init=False)
    due: str = field(init=False)

    def __post_init__(self) -> None:
        self.category = classify(f"{self.title} {self.description}")
        self.prio = priority(self.impact, self.urgency)
        self.due = sla_due(self.created_at, self.prio)

    def as_row(self) -> dict:
        return {
            "id": self.id, "title": self.title, "category": self.category,
            "priority": self.prio, "sla_due": self.due, "created_at": self.created_at,
        }


def triage_csv(input_path: str, output_path: str) -> dict:
    """Triage every row of input_path, write output_path, return a summary."""
    tickets = []
    with open(input_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tickets.append(Ticket(
                id=row["id"], title=row["title"], description=row["description"],
                impact=row["impact"], urgency=row["urgency"],
                created_at=row["created_at"],
            ))
    tickets.sort(key=lambda t: (t.prio, t.due))
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "category",
                                               "priority", "sla_due", "created_at"])
        writer.writeheader()
        writer.writerows(t.as_row() for t in tickets)
    summary = {"total": len(tickets)}
    for key in ("category", "prio"):
        counts: dict[str, int] = {}
        for t in tickets:
            value = t.category if key == "category" else t.prio
            counts[value] = counts.get(value, 0) + 1
        summary[f"by_{key}"] = counts
    return summary


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Triage IT support tickets from CSV.")
    parser.add_argument("input", help="Input CSV (id,title,description,impact,urgency,created_at)")
    parser.add_argument("output", help="Output triaged CSV path")
    parser.add_argument("--summary", help="Optional JSON summary path")
    args = parser.parse_args(argv)
    summary = triage_csv(args.input, args.output)
    if args.summary:
        with open(args.summary, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

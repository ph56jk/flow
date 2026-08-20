"""Reading the "Metadata cho agent" block off a HaviGroup ERP Task.

An ERP Task carries two YAML blocks, both returned by ``taskDetail`` and by
nothing else (``taskBoard`` does not include them):

``meta``
    What a person typed in the *Thuộc tính* panel::

        action_1: listing
        acc: acc32

``meta_auto``
    What ERP keeps in sync by itself — ``_task``, ``_title``, ``_status``,
    ``_priority``, ``_due``, ``_labels``, ``_assignees``, ``_agents``.  Read
    only; writing a key with a leading underscore is refused by ERP.

The agent reads ``meta`` to learn two things the Task alone cannot say: **what
work this Task is** (``action_*``) and **which Etsy account it belongs to**
(``acc``).  Before this, the account was pinned per runner process by the
``LISTING2_ERP_MACHINE_ID`` env var, so one runner could serve exactly one
account and a Task could not say where it wanted to go.

The parser is deliberately a small YAML subset, not a YAML library: the panel
writes one ``key: value`` per line and nothing else, and Listing 2 has no YAML
dependency.  Anything it cannot read is skipped rather than raised — a typo in
a metadata line must never take down a listing sweep.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


# ERP's own hint under the panel: "tên khoá chỉ gồm chữ thường không dấu, chữ
# số và gạch dưới, bắt đầu bằng chữ cái".  The system keys it generates add a
# leading underscore, so both shapes are accepted here.
_KEY_RE = re.compile(r"^_?[a-z][a-z0-9_]*$")
_ACTION_RE = re.compile(r"^action(?:_?(\d+))?$")
_DIGITS_RE = re.compile(r"(\d+)$")

# Keys that name the Etsy account, in the order they are trusted.
ACCOUNT_KEYS: Tuple[str, ...] = ("acc", "account", "etsy_acc", "etsy_account", "shop", "acc_id")
# Keys that pin one specific listing machine, overriding whatever the account
# would resolve to.
MACHINE_KEYS: Tuple[str, ...] = ("machine", "machine_id", "may", "pc", "vps")
# Keys that name a Google Flow browser profile.  Listing 2 does not route on
# this, but the image-generation half of the family (``erptrello``) picks its
# Flow account by profile label (``FLOW_CHROME_PROFILE_DIRS``), so the two
# repos read the same word for it when they are merged.
PROFILE_KEYS: Tuple[str, ...] = ("profile", "flow_profile", "flow_acc", "flow_account", "profile_label")
# Where ``taskDetail`` may name the Task above this one.  ERP's ``createTask``
# takes ``parentTask``, but the shape of the field it reads back has not been
# pinned down, so every plausible spelling is accepted and a Task with none of
# them simply has no parent as far as this module is concerned.
PARENT_KEYS: Tuple[str, ...] = ("parent_task", "parentTask", "parent", "parent_task_id", "parent_id")

# Every spelling of "this Task is an Etsy listing job" seen in the panel.
LISTING_ACTIONS = frozenset(
    {
        "listing",
        "listings",
        "list",
        "etsy",
        "etsy_listing",
        "listing_etsy",
        "dang_listing",
        "len_listing",
    }
)


def normalize_action(value: Any) -> str:
    """``"Listing Etsy"`` and ``"listing-etsy"`` are the same action."""
    text = " ".join(str(value or "").strip().lower().split())
    return re.sub(r"[\s\-]+", "_", text).strip("_")


def normalize_token(value: Any) -> str:
    """Same slug rule the service uses for account and machine ids."""
    text = str(value or "").strip().lower()
    text = "".join(ch if (ch.isalnum() or ch in "_-") else "-" for ch in text).strip("-")
    return "" if text in ("", "default", "auto", "any", "none", "null") else text


def _scalar(raw: str) -> str:
    """One YAML scalar as the panel writes it, flattened to text.

    Lists become a comma-joined string because every consumer here wants text;
    ``null`` and an empty list both become ``""`` so callers test one thing.
    """
    text = str(raw or "").strip()
    if len(text) >= 2 and text[0] in "\"'" and text[-1] == text[0]:
        return text[1:-1].strip()
    if text.startswith("[") and text.endswith("]"):
        items = [item.strip().strip("\"'") for item in text[1:-1].split(",")]
        return ", ".join(item for item in items if item)
    if text.startswith("{") and text.endswith("}"):
        return ""
    if text.lower() in {"null", "~", "none"}:
        return ""
    return text


def parse_meta_block(text: Any) -> Dict[str, str]:
    """Parse one metadata block into ``{key: value}``.

    Blank lines, comments, list items and anything without a ``:`` are skipped,
    as is any key ERP itself would refuse.  A repeated key keeps the last
    value, the way the panel's own save does.
    """
    values: Dict[str, str] = {}
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-") or ":" not in stripped:
            continue
        raw_key, _, raw_value = stripped.partition(":")
        key = raw_key.strip().strip("\"'").lower()
        if not _KEY_RE.match(key):
            continue
        values[key] = _scalar(raw_value)
    return values


def agent_users(detail: Optional[Mapping[str, Any]]) -> Tuple[str, ...]:
    """Bots ERP has assigned to a Task, in the order ERP returns them.

    The real assignment lives in ``taskDetail`` as ``agents[].bot_user`` — the
    same field the *Người phụ trách* box writes and ``addTaskAgent`` sets.  The
    ``meta_auto`` block only carries a rendered ``_agents`` line, used here as
    the fallback.  Reading it belongs next to the rest of "what this Task says
    about itself": the image half of the family already routes work by it.
    """
    source: Mapping[str, Any] = detail if isinstance(detail, Mapping) else {}
    users: List[str] = []
    for item in source.get("agents") or ():
        name = str((item or {}).get("bot_user") or "").strip() if isinstance(item, Mapping) else str(item or "").strip()
        if name and name not in users:
            users.append(name)
    return tuple(users)


def parent_task_id(detail: Optional[Mapping[str, Any]]) -> str:
    """The Task above this one, or ``""``.

    ERP does not push a parent's attributes down to its children — its
    ``createTask`` mutation takes no ``meta`` at all, and the image half of the
    family has to re-attach the parent's agents to every child by hand.  So
    inheritance, where we want it, is something this app does when it reads.
    """
    source: Mapping[str, Any] = detail if isinstance(detail, Mapping) else {}
    for key in PARENT_KEYS:
        value = source.get(key)
        if isinstance(value, Mapping):
            value = value.get("name") or value.get("id")
        text = str(value or "").strip()
        if text and text.lower() not in {"none", "null"}:
            return text
    return ""


@dataclass(frozen=True)
class TaskMeta:
    """The two metadata blocks of one ERP Task, parsed."""

    attributes: Dict[str, str] = field(default_factory=dict)
    auto: Dict[str, str] = field(default_factory=dict)
    raw: str = ""
    raw_auto: str = ""
    agents: Tuple[str, ...] = ()

    def get(self, *names: str) -> str:
        """First non-empty value among ``names``, user block before auto block."""
        for name in names:
            value = str(self.attributes.get(name) or "").strip()
            if value:
                return value
        for name in names:
            value = str(self.auto.get(name) or "").strip()
            if value:
                return value
        return ""

    @property
    def actions(self) -> List[str]:
        """Declared actions in panel order: ``action`` first, then ``action_1``…

        A single key may hold several actions (``action_1: listing, review``),
        which is why each value is split before it is normalized.
        """
        numbered: List[Tuple[int, str]] = []
        for key, value in self.attributes.items():
            match = _ACTION_RE.match(key)
            if not match or not str(value or "").strip():
                continue
            order = int(match.group(1)) if match.group(1) else 0
            numbered.append((order, str(value)))
        ordered: List[str] = []
        for _, value in sorted(numbered, key=lambda item: item[0]):
            for piece in re.split(r"[,;]", value):
                action = normalize_action(piece)
                if action and action not in ordered:
                    ordered.append(action)
        return ordered

    @property
    def declares_actions(self) -> bool:
        return bool(self.actions)

    def wants(self, wanted: Iterable[str]) -> bool:
        """Does the Task ask for one of ``wanted``?

        A Task with no ``action_*`` at all answers ``False``; callers decide
        whether "said nothing" means skip or means "carry on as before".
        """
        allowed = {normalize_action(item) for item in wanted}
        return any(action in allowed for action in self.actions)

    @property
    def is_listing(self) -> bool:
        return self.wants(LISTING_ACTIONS)

    @property
    def account_id(self) -> str:
        return normalize_token(self.get(*ACCOUNT_KEYS))

    @property
    def machine_id(self) -> str:
        return normalize_token(self.get(*MACHINE_KEYS))

    @property
    def flow_profile(self) -> str:
        """Flow browser profile label, kept as written.

        Profile labels are matched against ``FLOW_CHROME_PROFILE_DIRS`` by
        their text, and one of them may legitimately be called ``default``, so
        this one is not slugged the way an account id is.
        """
        return self.get(*PROFILE_KEYS)

    @property
    def agent_users(self) -> Tuple[str, ...]:
        """Assigned bots: the ERP field first, the ``_agents`` line as fallback."""
        if self.agents:
            return self.agents
        rendered = str(self.auto.get("_agents") or "").strip()
        if not rendered:
            return ()
        return tuple(part.strip() for part in re.split(r"[,;]", rendered) if part.strip())

    def assigned_to(self, bot_user: Any) -> bool:
        """Is ``bot_user`` one of the bots on this Task?"""
        wanted = str(bot_user or "").strip().lower()
        return bool(wanted) and any(wanted == item.lower() for item in self.agent_users)


def task_meta(source: Optional[Mapping[str, Any]]) -> TaskMeta:
    """Build :class:`TaskMeta` from a ``taskDetail`` payload or a normalized card.

    Accepts either shape so callers do not have to remember which one they
    hold: the raw ERP detail (``meta`` / ``meta_auto``) and the card the ERP
    adapter builds from it (same keys, plus ``_erp_raw``) both work.
    """
    detail: Mapping[str, Any] = source if isinstance(source, Mapping) else {}
    nested = detail.get("_erp_raw")
    if not str(detail.get("meta") or detail.get("meta_auto") or "").strip() and isinstance(nested, Mapping):
        detail = nested
    raw = str(detail.get("meta") or "")
    raw_auto = str(detail.get("meta_auto") or "")
    return TaskMeta(
        attributes=parse_meta_block(raw),
        auto=parse_meta_block(raw_auto),
        raw=raw,
        raw_auto=raw_auto,
        agents=agent_users(detail),
    )


def inherit(child: TaskMeta, parent: Optional[TaskMeta]) -> TaskMeta:
    """The child Task, with the parent filling in only what the child left out.

    A line the child wrote always wins — inheriting must never be able to move
    a Task somewhere its own metadata did not ask for.  ``meta_auto`` is never
    inherited: it describes one Task and nothing else.  Agents are inherited
    only when the child has none, which mirrors how children are created with
    the parent's agents in the first place.
    """
    if parent is None or not (parent.attributes or parent.agents):
        return child
    merged = dict(parent.attributes)
    merged.update(child.attributes)
    return TaskMeta(
        attributes=merged,
        auto=dict(child.auto),
        raw=child.raw,
        raw_auto=child.raw_auto,
        agents=child.agents or parent.agents,
    )


@dataclass(frozen=True)
class AccountRouting:
    """Where a Task should run, worked out from its metadata."""

    account_id: str = ""
    machine_id: str = ""
    account_source: str = ""
    machine_source: str = ""
    known_account: bool = False

    @property
    def resolved(self) -> bool:
        return bool(self.account_id or self.machine_id)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "machine_id": self.machine_id,
            "account_source": self.account_source,
            "machine_source": self.machine_source,
            "known_account": self.known_account,
        }


def machine_for_account(account_id: str, machine_ids: Sequence[str]) -> str:
    """Convention fallback: ``acc32`` runs on the machine numbered 32.

    The fleet is named ``etsy-vn32``, ``etsy-16``, ``capa-hinh``…  Matching on
    the trailing number is what an operator means by "acc32", and it is only
    used when nothing explicit said otherwise.  An ambiguous number (two
    machines ending in 32) resolves to nothing rather than to a guess.
    """
    account = normalize_token(account_id)
    if not account:
        return ""
    known = [normalize_token(item) for item in machine_ids]
    known = [item for item in known if item]
    if account in known:
        return account
    digits = _DIGITS_RE.search(account)
    if not digits:
        return ""
    number = str(int(digits.group(1)))
    matches = []
    for machine in known:
        found = _DIGITS_RE.search(machine)
        if found and str(int(found.group(1))) == number:
            matches.append(machine)
    return matches[0] if len(matches) == 1 else ""


def resolve_routing(
    meta: TaskMeta,
    *,
    known_accounts: Sequence[str] = (),
    known_machines: Sequence[str] = (),
    account_machines: Optional[Mapping[str, str]] = None,
) -> AccountRouting:
    """Turn ``acc: acc32`` into "which account, which machine".

    Order for the machine, most explicit first:

    1. ``machine:`` written on the Task itself,
    2. the machine configured for that account (``EtsyAccount.etsy_machine_id``
       or the ``FLOW_ERP_ACC_MACHINES`` map),
    3. the fleet-naming convention (``acc32`` → ``etsy-vn32``).

    Nothing is invented: an account with no machine anywhere returns an empty
    ``machine_id``, which leaves the queued task claimable by any machine of
    that account — the behaviour before metadata existed.
    """
    account_id = meta.account_id
    known_account_slugs = {normalize_token(item) for item in known_accounts}
    known_account_slugs.discard("")
    configured = {normalize_token(key): normalize_token(value) for key, value in (account_machines or {}).items()}

    machine_id = meta.machine_id
    machine_source = "meta_machine" if machine_id else ""
    if not machine_id and account_id:
        machine_id = configured.get(account_id, "")
        machine_source = "account_config" if machine_id else ""
    if not machine_id and account_id:
        machine_id = machine_for_account(account_id, known_machines)
        machine_source = "fleet_number" if machine_id else ""

    return AccountRouting(
        account_id=account_id,
        machine_id=machine_id,
        account_source="meta_acc" if account_id else "",
        machine_source=machine_source,
        known_account=bool(account_id and account_id in known_account_slugs),
    )

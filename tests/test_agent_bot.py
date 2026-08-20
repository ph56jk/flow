from __future__ import annotations

import asyncio
import json
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from flow_web.agent_bot import (
    DECISION_DELETE,
    DECISION_KEEP,
    DECISION_PENDING,
    AgentBot,
    AgentBotConfig,
    AgentBotError,
    AgentBotState,
    _RateLimiter,
    count_card_images,
    compact_status,
    is_idea_card,
    is_review_post,
    iter_review_posts,
    iter_tree_nodes,
    is_listing_card,
    task_has_agent,
    vote_decision,
)


BOT = "agent-kin-test-agent@bots.hvg.internal"


def comment(
    name: str,
    *,
    mine: int = 1,
    like: int = 0,
    dislike: int = 0,
    content: str = "[FLOW_V2_REVIEW job#0] Ảnh 1/2 chờ duyệt",
    attachments: List[Dict[str, Any]] | None = None,
    replies: List[Dict[str, Any]] | None = None,
    owner: str = BOT,
) -> Dict[str, Any]:
    """One comment shaped the way ``taskFull`` really returns them."""
    return {
        "name": name,
        "owner": owner,
        "is_bot": 1 if mine else 0,
        "mine": mine,
        "content": content,
        "like_count": like,
        "dislike_count": dislike,
        "my_vote": "",
        "attachments": attachments if attachments is not None else [{"file_name": f"{name}.png"}],
        "replies": replies or [],
    }


def task_node(name: str, *, agents: List[str] = (), comments: List[Dict[str, Any]] = (), subtasks=(), child_total: int = 0):
    return {
        "name": name,
        "subject": name,
        "agents": [{"bot_user": item} for item in agents],
        "comments": list(comments),
        "subtasks": list(subtasks),
        "children": [{"name": item["name"]} for item in subtasks],
        "child_total": child_total or len(subtasks),
    }


class FakeClient:
    """Only the six calls ``AgentBot`` makes, recording every write."""

    def __init__(self, projects: List[str], boards: Dict[str, List[Dict[str, Any]]], trees: Dict[str, Dict[str, Any]]):
        self._projects = projects
        self._boards = boards
        self._trees = trees
        self.deleted: List[tuple[str, str]] = []
        self.comments: List[tuple[str, str]] = []
        self.agents_added: List[tuple[str, str]] = []

    def task_projects(self) -> List[Dict[str, Any]]:
        return [{"name": name, "project_name": name} for name in self._projects]

    def task_board(self, project: str) -> List[Dict[str, Any]]:
        return self._boards.get(project, [])

    def task_full(self, name: str, depth: int = 1) -> Dict[str, Any]:
        return self._trees.get(name, {"root": {}})

    def add_comment(self, task: str, content: str, attachments=None, parent: str = "") -> Dict[str, Any]:
        self.comments.append((task, content))
        return {"ok": True, "linked": len(attachments or [])}

    def delete_comment(self, task: str, comment_id: str) -> Dict[str, Any]:
        self.deleted.append((task, comment_id))
        return {"ok": True, "files": 1, "replies": 0}

    def add_task_agent(self, task: str, bot_user: str) -> Dict[str, Any]:
        self.agents_added.append((task, bot_user))
        return {"ok": True}


def build_bot(client: FakeClient, tmp: Path, **overrides) -> AgentBot:
    config = AgentBotConfig(token="t0ken", bot_user=BOT, **overrides)
    return AgentBot(config, client=client, state=AgentBotState.load(tmp / "state.json"))


class VoteDecisionTests(unittest.TestCase):
    """Reading 👍/👎 counts into keep, delete, or "nobody has said"."""

    def test_more_dislikes_deletes_and_more_likes_keeps(self) -> None:
        self.assertEqual(DECISION_DELETE, vote_decision({"like_count": 0, "dislike_count": 1}))
        self.assertEqual(DECISION_DELETE, vote_decision({"like_count": 1, "dislike_count": 3}))
        self.assertEqual(DECISION_KEEP, vote_decision({"like_count": 1, "dislike_count": 0}))
        self.assertEqual(DECISION_KEEP, vote_decision({"like_count": 4, "dislike_count": 2}))

    def test_nobody_voted_decides_nothing(self) -> None:
        self.assertEqual(DECISION_PENDING, vote_decision({}))
        self.assertEqual(DECISION_PENDING, vote_decision({"like_count": 0, "dislike_count": 0}))

    def test_a_tie_is_undecided_rather_than_a_delete(self) -> None:
        # Deleting is not undoable, so a split room must leave the image alone
        # instead of letting whoever clicked first win.
        self.assertEqual(DECISION_PENDING, vote_decision({"like_count": 1, "dislike_count": 1}))
        self.assertEqual(DECISION_PENDING, vote_decision({"like_count": 3, "dislike_count": 3}))


class ReviewPostTests(unittest.TestCase):
    """Which comments the bot may act on at all."""

    def test_only_the_bots_own_posts_count(self) -> None:
        # The bot cannot delete somebody else's comment, so claiming one as
        # its work would mean promising a 👎 that never removes anything.
        self.assertTrue(is_review_post(comment("a", mine=1)))
        self.assertFalse(is_review_post(comment("a", mine=0, owner="phong.hothanh@havigroup.llc")))

    def test_the_bots_own_result_notes_are_not_review_posts(self) -> None:
        # Otherwise the next pass would tidy away the note the last pass left.
        note = comment("n", content="[AGENT_BOT] 👎 Đã gỡ ảnh a.png khỏi thẻ.", attachments=[])
        self.assertFalse(is_review_post(note))
        legacy = comment("r", content="[FLOW_V2_REVIEW_RESULT] ✅ Đã duyệt ảnh 1.", attachments=[])
        self.assertFalse(is_review_post(legacy))

    def test_a_bare_chat_message_from_the_bot_is_not_a_review_post(self) -> None:
        self.assertFalse(is_review_post(comment("c", content="Đã nhận việc", attachments=[])))

    def test_a_wordless_review_post_is_recognised_by_its_meta(self) -> None:
        # Bình luận ảnh chờ duyệt không còn chữ nào; dấu ở ``meta`` là thứ duy
        # nhất nói nó là việc của bot khi hàng đính kèm đọc về rỗng.
        wordless = comment("w", content="\u200b", attachments=[])
        wordless["meta"] = "[FLOW_V2_REVIEW abc#3]"
        self.assertTrue(is_review_post(wordless))

    def test_the_legacy_review_tag_counts_even_without_an_attachment_row(self) -> None:
        # Images published through the old REST upload path show an empty
        # attachments list, but the tag still says what the comment is.
        tagged = comment("t", content="[FLOW_V2_REVIEW abc#3] Ảnh 4/12 chờ duyệt", attachments=[])
        self.assertTrue(is_review_post(tagged))


class TreeWalkTests(unittest.TestCase):
    """``taskFull`` hides the real subtree behind ``subtasks``."""

    def test_the_walk_follows_subtasks_not_the_thin_children_list(self) -> None:
        child = task_node("TASK-2", comments=[comment("c2")])
        root = task_node("TASK-1", subtasks=[child])
        # ``children`` carries no comments at all; walking it would find none.
        self.assertEqual(["TASK-1", "TASK-2"], [node["name"] for node in iter_tree_nodes(root)])

    def test_replies_are_reviewed_alongside_top_level_comments(self) -> None:
        parent = comment("p", content="Ảnh nguồn cho AI", attachments=[], replies=[comment("r")])
        node = task_node("TASK-1", comments=[parent])
        self.assertEqual(["r"], [item["name"] for item in iter_review_posts(node)])

    def test_agent_membership_is_read_off_the_task(self) -> None:
        self.assertTrue(task_has_agent(task_node("T", agents=[BOT]), BOT))
        self.assertFalse(task_has_agent(task_node("T", agents=["agent-other@bots.hvg.internal"]), BOT))
        self.assertFalse(task_has_agent(task_node("T"), BOT))


class JanitorTests(unittest.TestCase):
    """👎 takes the image off the card, 👍 leaves it there."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _tree(self, *comments: Dict[str, Any]) -> Dict[str, Any]:
        return {"root": task_node("TASK-1", agents=[BOT], comments=list(comments))}

    def test_a_disliked_image_is_deleted_and_nothing_is_written_in_its_place(self) -> None:
        client = FakeClient([], {}, {})
        bot = build_bot(client, self.tmp)
        applied = bot.janitor_pass(self._tree(comment("c1", dislike=2)))

        self.assertEqual([{"decision": DECISION_DELETE, "comment": "c1"}], [
            {"decision": item["decision"], "comment": item["comment"]} for item in applied
        ])
        self.assertEqual([("TASK-1", "c1")], client.deleted)
        # The bot used to leave a "đã gỡ" note per image, which on a card of a
        # dozen images became the thing the reviewer scrolled past. The record
        # belongs in the app log, not on the card.
        self.assertEqual([], client.comments)

    def test_a_liked_image_stays_on_the_card(self) -> None:
        client = FakeClient([], {}, {})
        bot = build_bot(client, self.tmp)
        applied = bot.janitor_pass(self._tree(comment("c1", like=1)))

        self.assertEqual([DECISION_KEEP], [item["decision"] for item in applied])
        self.assertEqual([], client.deleted)

    def test_an_unvoted_image_is_left_completely_alone(self) -> None:
        client = FakeClient([], {}, {})
        bot = build_bot(client, self.tmp)
        self.assertEqual([], bot.janitor_pass(self._tree(comment("c1"))))
        self.assertEqual([], client.deleted)
        self.assertEqual([], client.comments)

    def test_a_decision_is_applied_once_even_if_the_card_still_shows_it(self) -> None:
        # The card is read again every poll, and a kept image keeps its 👍
        # forever: without the ledger the bot would re-decide it every pass.
        client = FakeClient([], {}, {})
        bot = build_bot(client, self.tmp)
        tree = self._tree(comment("c1", like=1))
        self.assertEqual(1, len(bot.janitor_pass(tree)))
        self.assertEqual([], bot.janitor_pass(tree))
        self.assertEqual([], client.comments)

    def test_a_ledger_written_to_disk_survives_a_restart(self) -> None:
        client = FakeClient([], {}, {})
        bot = build_bot(client, self.tmp)
        bot.janitor_pass(self._tree(comment("c1", dislike=1)))
        bot.state.save()

        restarted = build_bot(FakeClient([], {}, {}), self.tmp)
        self.assertTrue(restarted.state.already_handled("c1"))

    def test_dry_run_reports_the_decision_without_touching_the_card(self) -> None:
        client = FakeClient([], {}, {})
        bot = build_bot(client, self.tmp, dry_run=True)
        applied = bot.janitor_pass(self._tree(comment("c1", dislike=1)))

        self.assertEqual([DECISION_DELETE], [item["decision"] for item in applied])
        self.assertEqual([], client.deleted)
        self.assertEqual([], client.comments)
        # And it must not be recorded, or the real run would skip it.
        self.assertFalse(bot.state.already_handled("c1"))

    def test_a_failed_delete_is_not_recorded_as_done(self) -> None:
        class Refusing(FakeClient):
            def delete_comment(self, task: str, comment_id: str):
                raise AgentBotError("ERP từ chối xoá")

        client = Refusing([], {}, {})
        bot = build_bot(client, self.tmp)
        self.assertEqual([], bot.janitor_pass(self._tree(comment("c1", dislike=1))))
        # Next pass must try again rather than leave a disliked image up.
        self.assertFalse(bot.state.already_handled("c1"))

    def test_images_on_child_cards_are_cleaned_too(self) -> None:
        # One card per idea: the images live on the children, not the parent.
        client = FakeClient([], {}, {})
        bot = build_bot(client, self.tmp)
        child = task_node("TASK-2", comments=[comment("c2", dislike=1)])
        tree = {"root": task_node("TASK-1", agents=[BOT], subtasks=[child])}
        bot.janitor_pass(tree)
        self.assertEqual([("TASK-2", "c2")], client.deleted)


class ScopeTests(unittest.TestCase):
    """The ERP decides the scope, not the config file."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_no_configured_projects_means_every_project_the_bot_can_see(self) -> None:
        client = FakeClient(["PROJ-0013", "PROJ-0049"], {}, {})
        bot = build_bot(client, self.tmp)
        self.assertEqual(["PROJ-0013", "PROJ-0049"], bot.scope_projects())

    def test_a_configured_project_the_bot_cannot_see_is_dropped(self) -> None:
        # Being named in .env does not grant Project User membership, and
        # pretending it does would only produce permission errors later.
        client = FakeClient(["PROJ-0013"], {}, {})
        bot = build_bot(client, self.tmp, projects=("PROJ-0013", "PROJ-9999"))
        self.assertEqual(["PROJ-0013"], bot.scope_projects())

    def test_the_scope_is_written_down_for_the_rest_of_the_app(self) -> None:
        # Hàng rào dự án của app đọc đúng sổ này, nên "thêm bot vào board" là
        # thao tác duy nhất — không phải khai lại board ở .env.local.
        client = FakeClient(["PROJ-0013", "PROJ-0049"], {}, {})
        bot = build_bot(client, self.tmp)
        bot.scope_projects()
        self.assertEqual(["PROJ-0013", "PROJ-0049"], bot.state.projects)

    def test_a_narrowed_scope_is_what_gets_written_down(self) -> None:
        client = FakeClient(["PROJ-0013", "PROJ-0049"], {}, {})
        bot = build_bot(client, self.tmp, projects=("PROJ-0013",))
        bot.scope_projects()
        self.assertEqual(["PROJ-0013"], bot.state.projects)

    def test_the_scope_survives_a_restart(self) -> None:
        # App vừa bật lại thì bot còn ngủ hết một chu kỳ mới quét; hàng rào
        # phải biết ngay chứ không đợi hai phút.
        client = FakeClient(["PROJ-0013", "PROJ-0049"], {}, {})
        bot = build_bot(client, self.tmp)
        bot.scope_projects()
        bot.state.save()
        self.assertEqual(
            ["PROJ-0013", "PROJ-0049"], AgentBotState.load(self.tmp / "state.json").projects
        )

    def test_a_board_the_bot_was_dropped_from_disappears_from_the_note(self) -> None:
        client = FakeClient(["PROJ-0013"], {}, {})
        bot = build_bot(client, self.tmp)
        bot.state.projects = ["PROJ-0013", "PROJ-0049"]
        bot.scope_projects()
        self.assertEqual(["PROJ-0013"], bot.state.projects)


class RunOnceTests(unittest.TestCase):
    """One full pass: find the attached cards, judge them, run them."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _client(self) -> FakeClient:
        mine = {"name": "TASK-1", "agents": [{"bot_user": BOT}], "child_total": 1}
        theirs = {"name": "TASK-9", "agents": [{"bot_user": "agent-other@bots.hvg.internal"}], "child_total": 0}
        child = task_node("TASK-2", comments=[comment("c1", dislike=1), comment("c2", like=1)])
        return FakeClient(
            ["PROJ-0049"],
            {"PROJ-0049": [mine, theirs]},
            {"TASK-1": {"root": task_node("TASK-1", agents=[BOT], subtasks=[child])}},
        )

    def test_only_the_cards_this_bot_is_attached_to_are_touched(self) -> None:
        client = self._client()
        bot = build_bot(client, self.tmp, autorun=False)
        summary = asyncio.run(bot.run_once())

        self.assertEqual(["TASK-1"], summary["tasks"])
        self.assertEqual(1, summary["deleted"])
        self.assertEqual(1, summary["kept"])
        self.assertEqual([("TASK-2", "c1")], client.deleted)

    def test_the_attached_parent_card_is_handed_to_the_run_hook(self) -> None:
        client = self._client()
        seen: List[str] = []

        async def hook(task_id: str) -> Dict[str, Any]:
            seen.append(task_id)
            return {"queued": [{"task_id": "TASK-2"}]}

        bot = build_bot(client, self.tmp)
        bot.autorun_hook = hook
        summary = asyncio.run(bot.run_once())

        self.assertEqual(["TASK-1"], seen)
        self.assertEqual([{"task": "TASK-1", "result": {"queued": [{"task_id": "TASK-2"}]}}], summary["autorun"])

    def test_the_same_card_is_not_re_run_inside_the_cooldown(self) -> None:
        client = self._client()
        calls: List[str] = []

        async def hook(task_id: str) -> Dict[str, Any]:
            calls.append(task_id)
            return {}

        bot = build_bot(client, self.tmp, autorun_cooldown_seconds=900)
        bot.autorun_hook = hook
        asyncio.run(bot.run_once())
        asyncio.run(bot.run_once())
        self.assertEqual(["TASK-1"], calls)

    def test_a_hook_that_raises_does_not_break_the_pass(self) -> None:
        client = self._client()

        async def hook(task_id: str) -> Dict[str, Any]:
            raise RuntimeError("Flow đang bận")

        bot = build_bot(client, self.tmp)
        bot.autorun_hook = hook
        summary = asyncio.run(bot.run_once())
        self.assertEqual("Flow đang bận", summary["autorun"][0]["error"])
        # The janitor still did its half of the job.
        self.assertEqual(1, summary["deleted"])

    def test_a_bot_in_no_project_reports_that_instead_of_failing(self) -> None:
        bot = build_bot(FakeClient([], {}, {}), self.tmp)
        summary = asyncio.run(bot.run_once())
        self.assertEqual([], summary["projects"])
        self.assertIn("dự án", summary["reason"])

    def test_no_token_means_the_bot_reports_itself_off(self) -> None:
        bot = AgentBot(AgentBotConfig(), client=FakeClient([], {}, {}), state=AgentBotState.load(self.tmp / "s.json"))
        self.assertFalse(asyncio.run(bot.run_once())["enabled"])


class BoardScopeTests(unittest.TestCase):
    """Thêm bot vào dự án là đủ — không phải gắn vào từng thẻ."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.calls: List[str] = []

    async def _hook(self, task_id: str) -> Dict[str, Any]:
        self.calls.append(task_id)
        return {"queued": []}

    def _client(self, board: List[Dict[str, Any]]) -> FakeClient:
        trees = {
            item["name"]: {"root": task_node(item["name"], subtasks=[task_node(f"{item['name']}-c")])}
            for item in board
        }
        for name, tree in trees.items():
            root = tree["root"]
            source = next(item for item in board if item["name"] == name)
            root["agents"] = source.get("agents") or []
            root["status"] = source.get("status") or ""
            root["child_total"] = source.get("child_total", 1)
        return FakeClient(["PROJ-0013"], {"PROJ-0013": board}, trees)

    def _run(self, board: List[Dict[str, Any]], **overrides) -> Dict[str, Any]:
        bot = build_bot(self._client(board), self.tmp, **overrides)
        bot.autorun_hook = self._hook
        return asyncio.run(bot.run_once())

    def test_an_idea_card_nobody_attached_the_bot_to_is_still_run(self) -> None:
        summary = self._run([{"name": "TASK-1", "child_total": 3, "status": "Working"}])
        self.assertEqual(["TASK-1"], summary["tasks"])
        self.assertEqual(["TASK-1"], self.calls)

    def test_a_card_with_no_children_is_not_an_idea_card(self) -> None:
        summary = self._run([{"name": "TASK-1", "child_total": 0, "status": "Open"}])
        self.assertEqual([], summary["tasks"])
        self.assertEqual([], self.calls)

    def test_a_finished_or_cancelled_card_is_left_closed(self) -> None:
        board = [
            {"name": "TASK-1", "child_total": 2, "status": "Completed"},
            {"name": "TASK-2", "child_total": 2, "status": "Cancelled"},
        ]
        self.assertEqual([], self._run(board)["tasks"])
        self.assertEqual([], self.calls)

    def test_attaching_the_bot_to_one_card_narrows_that_project_to_it(self) -> None:
        # Gắn vào một thẻ chỉ có một nghĩa: chạy đúng thẻ này.
        board = [
            {"name": "TASK-1", "child_total": 2, "status": "Working"},
            {"name": "TASK-2", "child_total": 2, "status": "Working", "agents": [{"bot_user": BOT}]},
        ]
        summary = self._run(board)
        self.assertEqual(["TASK-2"], summary["tasks"])
        self.assertEqual(["TASK-2"], self.calls)

    def test_a_card_carrying_somebody_elses_bot_is_not_taken_over(self) -> None:
        board = [
            {"name": "TASK-1", "child_total": 2, "status": "Working"},
            {
                "name": "TASK-2",
                "child_total": 2,
                "status": "Working",
                "agents": [{"bot_user": "agent-other@bots.hvg.internal"}],
            },
        ]
        self.assertEqual(["TASK-1"], self._run(board)["tasks"])

    def test_card_scope_still_waits_to_be_attached_to_a_card(self) -> None:
        board = [{"name": "TASK-1", "child_total": 2, "status": "Working"}]
        self.assertEqual([], self._run(board, scope="card")["tasks"])
        self.assertEqual([], self.calls)

    def test_a_whole_board_does_not_become_a_whole_board_of_jobs_at_once(self) -> None:
        # Một trình duyệt, một phiên Flow: xếp cả board vào hàng chỉ làm hàng
        # đợi dài chứ không nhanh hơn.
        board = [
            {"name": f"TASK-{index}", "child_total": 2, "status": "Working"} for index in range(1, 6)
        ]
        summary = self._run(board, max_cards_per_scan=2)
        self.assertEqual(2, len(self.calls))
        # Nhưng phiếu 👍/👎 thì vẫn được đọc trên toàn bộ thẻ.
        self.assertEqual(5, len(summary["tasks"]))


class ListingCardTests(unittest.TestCase):
    """Một agent, một thẻ, hai chặng: làm ảnh xong rồi mới đăng lên Etsy.

    Thẻ nói mình là listing (``action_1: listing``) vẫn đi qua nửa làm ảnh —
    ảnh phải có từ đâu đó, và nửa listing không tạo ảnh, nó chỉ chép bộ ảnh
    đang nằm trên thẻ sang máy Etsy. Chặng đăng chỉ mở khi người duyệt đã bấm
    xong 👍/👎. Thẻ ảnh không viết ``action_*`` nào, nên im lặng vẫn là "làm
    như cũ".
    """

    LISTING_META = "action_1: listing\nacc: acc32"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.calls: List[str] = []

    async def _hook(self, task_id: str) -> Dict[str, Any]:
        self.calls.append(task_id)
        return {"queued": []}

    def _run(self, roots: List[Dict[str, Any]], listing_hook=None):
        rows = [
            {
                "name": root["name"],
                "child_total": root.get("child_total", 0),
                "status": "Working",
                "agents": root.get("agents") or [],
                "parent_task": "",
            }
            for root in roots
        ]
        client = FakeClient(
            ["PROJ-0013"],
            {"PROJ-0013": rows},
            {root["name"]: {"root": root} for root in roots},
        )
        bot = build_bot(client, self.tmp)
        bot.autorun_hook = self._hook
        bot.listing_hook = listing_hook
        return asyncio.run(bot.run_once()), client

    def _listing_root(self, name: str = "TASK-L", **kwargs) -> Dict[str, Any]:
        return {**task_node(name, agents=[BOT], **kwargs), "meta": self.LISTING_META}

    def _approved(self, name: str = "TASK-L") -> Dict[str, Any]:
        """Thẻ listing đã chạy xong ảnh và người duyệt đã bấm 👍."""
        return self._listing_root(
            name, comments=[comment("L-1", like=1), comment("L-2", like=2)]
        )

    async def _queued(self, task_id: str, root: Dict[str, Any]) -> Dict[str, Any]:
        return {"queue_task_id": "etsy-copy-1", "machine_id": "etsy-vn32"}

    def test_the_shape_written_in_the_panel_is_what_marks_a_listing_card(self) -> None:
        self.assertTrue(is_listing_card(self._listing_root()))
        # Thật sự lấy từ thẻ ảnh đang chạy trên ERP, không phải bịa.
        self.assertFalse(is_listing_card({"meta": "sku: \nproduct: khan tay\nfatheridea:"}))
        self.assertFalse(is_listing_card({"meta": "prompt:"}))
        self.assertFalse(is_listing_card({}))

    # ── chặng 1: thẻ listing vẫn phải có ảnh trước đã ──────────────────

    def test_a_listing_card_with_no_images_yet_goes_through_the_image_half(self) -> None:
        # Nếu nửa listing chiếm luôn thẻ ngay từ đầu thì sẽ không bao giờ có
        # ảnh nào để nó đăng.
        root = self._listing_root(subtasks=[task_node("TASK-L-a")])
        summary, _ = self._run([root], listing_hook=self._queued)

        self.assertEqual(["TASK-L"], self.calls)
        self.assertEqual("thẻ chưa có ảnh nào để đăng", summary["listing"][0]["waiting"])

    def test_a_card_still_waiting_on_a_thumb_is_not_handed_over(self) -> None:
        root = self._listing_root(comments=[comment("L-1", like=1), comment("L-2")])
        handed: List[str] = []

        async def listing_hook(task_id: str, node: Dict[str, Any]) -> Dict[str, Any]:
            handed.append(task_id)
            return {"queue_task_id": "x"}

        summary, _ = self._run([root], listing_hook=listing_hook)

        self.assertEqual([], handed)
        self.assertIn("chờ 👍/👎", summary["listing"][0]["waiting"])

    def test_a_card_whose_images_were_all_rejected_is_not_published_empty(self) -> None:
        root = self._listing_root(comments=[comment("L-1", dislike=1)])
        summary, client = self._run([root], listing_hook=self._queued)

        self.assertEqual("không còn ảnh nào được giữ", summary["listing"][0]["waiting"])
        # Phiếu 👎 vẫn được thi hành như mọi thẻ khác.
        self.assertEqual([("TASK-L", "L-1")], client.deleted)

    # ── chặng 2: ảnh đã chốt thì giao đi ───────────────────────────────

    def test_an_approved_card_is_handed_over_with_the_card_itself(self) -> None:
        handed: List[tuple[str, str]] = []

        async def listing_hook(task_id: str, root: Dict[str, Any]) -> Dict[str, Any]:
            # Nhận cả thẻ, không chỉ mã: bên kia cần ``meta`` để biết máy nào.
            handed.append((task_id, str(root.get("meta") or "")))
            return {"queue_task_id": "etsy-copy-1", "machine_id": "etsy-vn32"}

        summary, _ = self._run([self._approved()], listing_hook=listing_hook)

        self.assertEqual([("TASK-L", self.LISTING_META)], handed)
        self.assertEqual(
            {"queue_task_id": "etsy-copy-1", "machine_id": "etsy-vn32"},
            summary["listing"][0]["result"],
        )

    def test_a_card_already_sent_to_etsy_is_not_run_for_images_again(self) -> None:
        summary, _ = self._run([self._approved()], listing_hook=self._queued)
        self.assertEqual([], self.calls)
        self.assertEqual([], summary["autorun"])

    def test_with_no_listing_backend_the_card_is_reported_not_swallowed(self) -> None:
        # Bỏ qua âm thầm trông y hệt thẻ hỏng, mà người dùng vừa gắn agent vào nó.
        summary, _ = self._run([self._approved()])
        self.assertIn("ERP_LISTING_API_URL", summary["listing"][0]["skipped"])

    def test_a_listing_backend_that_is_down_does_not_break_the_sweep(self) -> None:
        async def listing_hook(task_id: str, root: Dict[str, Any]) -> Dict[str, Any]:
            raise RuntimeError("Bản Listing đang tắt")

        image = task_node("TASK-1", agents=[BOT], subtasks=[task_node("TASK-1-a")])
        summary, _ = self._run([self._approved(), image], listing_hook=listing_hook)

        self.assertEqual("Bản Listing đang tắt", summary["listing"][0]["error"])
        # Nửa làm ảnh vẫn chạy hết lượt của nó.
        self.assertEqual(["TASK-1"], self.calls)

    def test_a_card_the_listing_half_declines_can_still_be_retried(self) -> None:
        # "Thẻ đã ở cột Done" là câu trả lời của lần này thôi; người dùng sửa
        # thẻ rồi thì lượt sau phải giao lại được.
        sent: List[str] = []

        async def listing_hook(task_id: str, root: Dict[str, Any]) -> Dict[str, Any]:
            sent.append(task_id)
            return {"machine_id": "etsy-vn32", "skipped": "thẻ đã ở cột Done"}

        root = self._approved()
        rows = [{"name": "TASK-L", "child_total": 0, "status": "Working",
                 "agents": [{"bot_user": BOT}], "parent_task": ""}]
        client = FakeClient(["PROJ-0013"], {"PROJ-0013": rows}, {"TASK-L": {"root": root}})
        bot = build_bot(client, self.tmp, autorun_cooldown_seconds=0)
        bot.listing_hook = listing_hook
        asyncio.run(bot.run_once())
        asyncio.run(bot.run_once())

        self.assertEqual(["TASK-L", "TASK-L"], sent)

    # ── không giao hai lần ─────────────────────────────────────────────

    def test_the_same_card_is_never_published_twice(self) -> None:
        # Hai lần đăng là hai bản nháp trong shop cho cùng một sản phẩm, nên
        # đây là sổ ghi vĩnh viễn chứ không phải hàng rào thời gian.
        sent: List[str] = []

        async def listing_hook(task_id: str, root: Dict[str, Any]) -> Dict[str, Any]:
            sent.append(task_id)
            return {"queue_task_id": "etsy-copy-1", "machine_id": "etsy-vn32"}

        root = self._approved()
        rows = [{"name": "TASK-L", "child_total": 0, "status": "Working",
                 "agents": [{"bot_user": BOT}], "parent_task": ""}]
        client = FakeClient(["PROJ-0013"], {"PROJ-0013": rows}, {"TASK-L": {"root": root}})
        bot = build_bot(client, self.tmp, autorun_cooldown_seconds=0)
        bot.listing_hook = listing_hook
        asyncio.run(bot.run_once())
        asyncio.run(bot.run_once())

        self.assertEqual(["TASK-L"], sent)

    def test_a_restart_does_not_forget_what_was_already_published(self) -> None:
        sent: List[str] = []

        async def listing_hook(task_id: str, root: Dict[str, Any]) -> Dict[str, Any]:
            sent.append(task_id)
            return {"queue_task_id": "etsy-copy-1", "machine_id": "etsy-vn32"}

        rows = [{"name": "TASK-L", "child_total": 0, "status": "Working",
                 "agents": [{"bot_user": BOT}], "parent_task": ""}]
        for _ in range(2):
            client = FakeClient(["PROJ-0013"], {"PROJ-0013": rows}, {"TASK-L": {"root": self._approved()}})
            bot = build_bot(client, self.tmp, autorun_cooldown_seconds=0)
            bot.listing_hook = listing_hook
            asyncio.run(bot.run_once())

        self.assertEqual(["TASK-L"], sent)

    def test_a_second_sweep_inside_the_cooldown_does_not_hand_over_again(self) -> None:
        # Hàng rào thứ hai, cho lượt giao chưa kịp ghi sổ.
        state = AgentBotState.load(self.tmp / "state.json")
        state.mark_autorun("listing:TASK-L")
        state.save()

        summary, _ = self._run([self._approved()], listing_hook=self._queued)
        self.assertIn("nguội", summary["listing"][0]["skipped"])

    # ── phần còn lại của lượt quét không bị ảnh hưởng ──────────────────

    def test_a_listing_card_is_still_this_agent_s_card(self) -> None:
        root = self._listing_root(subtasks=[task_node("TASK-L-a")])
        summary, client = self._run([root])

        self.assertEqual(["TASK-L"], summary["tasks"])
        self.assertEqual([("TASK-L-a", BOT)], client.agents_added)

    def test_an_image_card_in_the_same_sweep_is_untouched_by_all_this(self) -> None:
        image = task_node(
            "TASK-1",
            agents=[BOT],
            subtasks=[task_node("TASK-1-a", comments=[comment("c1", dislike=1)])],
        )
        summary, client = self._run([self._approved(), image], listing_hook=self._queued)

        self.assertEqual(["TASK-L"], [item["task"] for item in summary["listing"]])
        self.assertEqual(["TASK-1"], self.calls)
        self.assertEqual([("TASK-1-a", "c1")], client.deleted)


class AgentInheritanceTests(unittest.TestCase):
    """Gắn bot vào thẻ cha là gắn cho cả cụm: thẻ con được gắn theo."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.calls: List[str] = []

    async def _hook(self, task_id: str) -> Dict[str, Any]:
        self.calls.append(task_id)
        return {"queued": []}

    def _run(self, root: Dict[str, Any], board=None, **overrides):
        name = root["name"]
        rows = board or [
            {
                "name": name,
                "child_total": root.get("child_total", 0),
                "status": "Working",
                "agents": root.get("agents") or [],
                "parent_task": root.get("parent_task") or "",
            }
        ]
        client = FakeClient(["PROJ-0013"], {"PROJ-0013": rows}, {name: {"root": root}})
        bot = build_bot(client, self.tmp, **overrides)
        bot.autorun_hook = self._hook
        return asyncio.run(bot.run_once()), client

    def test_children_of_an_attached_parent_are_attached_too(self) -> None:
        root = task_node(
            "TASK-1",
            agents=[BOT],
            subtasks=[task_node("TASK-1-a"), task_node("TASK-1-b")],
        )
        summary, client = self._run(root)
        self.assertEqual([("TASK-1-a", BOT), ("TASK-1-b", BOT)], client.agents_added)
        self.assertEqual(["TASK-1-a", "TASK-1-b"], [item["task"] for item in summary["inherited"]])

    def test_a_child_that_already_carries_the_bot_is_left_alone(self) -> None:
        root = task_node(
            "TASK-1",
            agents=[BOT],
            subtasks=[task_node("TASK-1-a", agents=[BOT]), task_node("TASK-1-b")],
        )
        _, client = self._run(root)
        self.assertEqual([("TASK-1-b", BOT)], client.agents_added)

    def test_grandchildren_are_attached_as_well(self) -> None:
        # Cụm việc sâu hai tầng vẫn là một cụm việc.
        deep = task_node("TASK-1-a", subtasks=[task_node("TASK-1-a-1")])
        summary, client = self._run(task_node("TASK-1", agents=[BOT], subtasks=[deep]))
        self.assertEqual(
            [("TASK-1-a", BOT), ("TASK-1-a-1", BOT)], client.agents_added
        )
        self.assertEqual(2, len(summary["inherited"]))

    def test_a_card_the_bot_only_reached_through_the_project_spreads_nothing(self) -> None:
        # Không ai gắn bot vào đâu cả: bot đang làm vì nó ở trong dự án, và tự
        # đi gắn mình vào từng thẻ con là ghi lên thẻ của người khác.
        root = task_node("TASK-1", subtasks=[task_node("TASK-1-a")], child_total=1)
        _, client = self._run(root)
        self.assertEqual([], client.agents_added)

    def test_somebody_elses_bot_on_the_parent_spreads_nothing(self) -> None:
        root = task_node("TASK-1", agents=["agent-other@bots.hvg.internal"], subtasks=[task_node("TASK-1-a")])
        _, client = self._run(root)
        self.assertEqual([], client.agents_added)

    def test_dry_run_says_what_it_would_attach_and_writes_nothing(self) -> None:
        root = task_node("TASK-1", agents=[BOT], subtasks=[task_node("TASK-1-a")])
        summary, client = self._run(root, dry_run=True)
        self.assertEqual([], client.agents_added)
        self.assertEqual([{"task": "TASK-1-a", "dry_run": True}], summary["inherited"])

    def test_the_parent_still_gets_the_scan_slot_its_children_would_have_eaten(self) -> None:
        # Sau khi lan xuống, thẻ con cũng mang bot nên cũng lọt bộ lọc "gắn
        # đích danh". Thẻ cha đã chứa sẵn cây của con, nên chạy thêm từng thẻ
        # con là vừa thừa vừa ăn mất trần mỗi lượt.
        board = [
            {"name": "TASK-1", "child_total": 2, "status": "Working", "agents": [{"bot_user": BOT}]},
            {"name": "TASK-1-a", "child_total": 0, "status": "Working",
             "agents": [{"bot_user": BOT}], "parent_task": "TASK-1"},
            {"name": "TASK-1-b", "child_total": 0, "status": "Working",
             "agents": [{"bot_user": BOT}], "parent_task": "TASK-1"},
        ]
        root = task_node("TASK-1", agents=[BOT], subtasks=[task_node("TASK-1-a"), task_node("TASK-1-b")])
        summary, _ = self._run(root, board=board)
        self.assertEqual(["TASK-1"], summary["tasks"])
        self.assertEqual(["TASK-1"], self.calls)

    def test_a_child_attached_on_its_own_is_still_run_on_its_own(self) -> None:
        # Cha không gắn thì gắn vào con là người dùng cố ý chỉ đúng thẻ đó.
        board = [
            {"name": "TASK-1", "child_total": 2, "status": "Working"},
            {"name": "TASK-1-a", "child_total": 2, "status": "Working",
             "agents": [{"bot_user": BOT}], "parent_task": "TASK-1"},
        ]
        root = task_node("TASK-1-a", agents=[BOT], child_total=2)
        client = FakeClient(["PROJ-0013"], {"PROJ-0013": board}, {"TASK-1-a": {"root": root}})
        bot = build_bot(client, self.tmp)
        bot.autorun_hook = self._hook
        summary = asyncio.run(bot.run_once())
        self.assertEqual(["TASK-1-a"], summary["tasks"])
        self.assertEqual(["TASK-1-a"], self.calls)


class IdeaIntakeGateTests(unittest.TestCase):
    """Thẻ Idea vừa được thả ảnh: chưa có thẻ con nhưng vẫn phải nhận."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.calls: List[str] = []

    async def _hook(self, task_id: str) -> Dict[str, Any]:
        self.calls.append(task_id)
        return {"created": [{"task_id": "TASK-NEW-0"}], "queued": []}

    @staticmethod
    def _card(name: str, *, cover: str = "", images: tuple = (), child_total: int = 0, is_group: int = 1):
        root = task_node(name, child_total=child_total)
        root.update({"status": "Working", "cover_image": cover, "is_group": is_group})
        root["comments"] = [
            {
                "name": f"drop-{index}",
                "content": "",
                "attachments": [{"file_url": url, "file_name": Path(url).name}],
            }
            for index, url in enumerate(images)
        ]
        return root

    def _run(self, root: Dict[str, Any], attachment_count: int = 0) -> Dict[str, Any]:
        board = [
            {
                "name": root["name"],
                "child_total": root["child_total"],
                "status": root["status"],
                "is_group": root["is_group"],
                "attachment_count": attachment_count,
            }
        ]
        client = FakeClient(["PROJ-0013"], {"PROJ-0013": board}, {root["name"]: {"root": root}})
        bot = build_bot(client, self.tmp)
        bot.autorun_hook = self._hook
        return asyncio.run(bot.run_once())

    def test_a_card_with_a_second_image_and_no_children_yet_is_run(self) -> None:
        # Người dùng vừa thả ảnh idea lên thẻ; thẻ con chưa tồn tại vì chính
        # lượt chạy này mới tạo ra nó.
        root = self._card(
            "TASK-1", cover="/private/files/khan-tay.jpg", images=("/private/files/tho-noel.jpg",)
        )
        self.assertEqual(["TASK-1"], self._run(root)["tasks"])
        self.assertEqual(["TASK-1"], self.calls)

    def test_a_card_carrying_only_its_product_photo_is_left_alone(self) -> None:
        root = self._card("TASK-1", cover="/private/files/khan-tay.jpg")
        self.assertEqual([], self.calls)
        self._run(root)
        self.assertEqual([], self.calls)

    def test_a_plain_card_with_no_children_is_still_not_an_idea_card(self) -> None:
        self.assertFalse(is_idea_card({"name": "TASK-1", "child_total": 0, "status": "Open"}))
        self.assertTrue(is_idea_card({"name": "TASK-1", "child_total": 0, "status": "Open", "is_group": 1}))
        self.assertTrue(is_idea_card({"name": "TASK-1", "child_total": 2, "status": "Open"}))
        # Thẻ trắng vừa được kéo ảnh sản phẩm + ảnh idea vào: đây mới là đường
        # người dùng thật đi, và nó không phải thẻ nhóm.
        self.assertTrue(
            is_idea_card({"name": "TASK-1", "child_total": 0, "status": "Open", "attachment_count": 2})
        )
        # Một tệp là ảnh sản phẩm đứng một mình, chưa có idea nào.
        self.assertFalse(
            is_idea_card({"name": "TASK-1", "child_total": 0, "status": "Open", "attachment_count": 1})
        )

    def test_a_card_whose_images_were_dragged_straight_on_is_still_run(self) -> None:
        # taskFull không trả tệp treo thẳng trên thẻ, nên thẻ này đọc về trắng
        # trơn: không bìa, không bình luận, không thẻ con. Chỉ dòng của nó trên
        # bảng dự án biết là đang có 3 tệp.
        root = self._card("TASK-1", is_group=0)
        self.assertEqual(["TASK-1"], self._run(root, attachment_count=3)["tasks"])
        self.assertEqual(["TASK-1"], self.calls)

    def test_a_dragged_on_product_photo_by_itself_is_left_alone(self) -> None:
        root = self._card("TASK-1", is_group=0)
        self._run(root, attachment_count=1)
        self.assertEqual([], self.calls)

    def test_flow_output_images_are_not_counted_as_dropped_ideas(self) -> None:
        # Nếu tính cả ảnh Flow thì thẻ nào chạy xong cũng trông như vừa được
        # thả thêm ảnh, và bot sẽ chạy lại nó mãi.
        node = {
            "cover_image": "/private/files/khan-tay.jpg",
            "comments": [
                {
                    "content": "[FLOW_V2_ARTIFACT] flow-1.png",
                    "attachments": [{"file_url": "/files/flow-1.png", "file_name": "flow-1.png"}],
                },
                {"content": "", "attachments": [{"file_url": "/files/ghi-chu.pdf", "file_name": "ghi-chu.pdf"}]},
            ],
        }
        self.assertEqual(1, count_card_images(node))
        # Dòng bảng đếm cả tệp treo thẳng trên thẻ, thứ taskFull không thấy;
        # lấy số lớn hơn chứ không cộng, hai bên đếm chồng lên nhau.
        self.assertEqual(3, count_card_images(node, {"attachment_count": 3}))
        self.assertEqual(1, count_card_images(node, {"attachment_count": 0}))

    def test_images_living_inside_a_comment_are_counted(self) -> None:
        # taskFull trả bình luận với attachments rỗng và đúng một ảnh đại diện,
        # dù taskDetail của chính bình luận ấy có cả chục tấm. Không đếm ảnh đại
        # diện thì thẻ kiểu này đọc về mỗi tấm bìa và bị từ chối vĩnh viễn.
        node = {
            "cover_image": "/private/files/khan-tay.jpg",
            "comments": [{"content": "(đã đính kèm tệp)", "attachments": [], "image": "/files/tho-noel.jpg"}],
        }
        self.assertEqual(2, count_card_images(node))

    def test_a_flow_artifact_comment_image_is_not_counted(self) -> None:
        node = {
            "cover_image": "/private/files/khan-tay.jpg",
            "comments": [
                {"content": "[FLOW_V2_ARTIFACT] flow-1.png", "attachments": [], "image": "/files/flow-1.png"},
                {"content": "", "attachments": [], "image": "/files/flow-2.png"},
                {"content": "", "attachments": [], "image": "/files/ghi-chu.pdf"},
            ],
        }
        self.assertEqual(1, count_card_images(node))

    def test_a_flow_image_marked_only_in_meta_is_not_counted(self) -> None:
        # Ảnh Flow bây giờ lên thẻ không kèm chữ nào, dấu nằm ở ``meta``. Đọc
        # sót dấu ấy thì thẻ vừa chạy xong trông như vừa được thả ảnh mới, và
        # bot sẽ chạy lại nó vòng này qua vòng khác.
        node = {
            "cover_image": "/private/files/khan-tay.jpg",
            "comments": [
                {
                    "content": "\u200b",
                    "meta": "[FLOW_V2_ARTIFACT] flow-1.png",
                    "attachments": [{"file_url": "/files/flow-1.png", "file_name": "flow-1.png"}],
                    "image": "/files/flow-1.png",
                },
            ],
        }
        self.assertEqual(1, count_card_images(node))

    def test_a_card_whose_ideas_sit_in_one_comment_is_run(self) -> None:
        root = task_node("TASK-1", child_total=0)
        root.update({"status": "Open", "cover_image": "/private/files/khan-tay.jpg", "is_group": 1})
        root["comments"] = [{"name": "c1", "content": "(đã đính kèm tệp)", "attachments": [], "image": "/files/tho-noel.jpg"}]
        self.assertEqual(["TASK-1"], self._run(root)["tasks"])
        self.assertEqual(["TASK-1"], self.calls)


class ClosedColumnTests(unittest.TestCase):
    """Cột kết thúc phải được nhận ra kể cả khi board đặt tên tiếng Việt."""

    def _card(self, status: str) -> Dict[str, Any]:
        return {"name": "TASK-1", "child_total": 3, "status": status}

    def test_the_real_columns_of_proj_0013(self) -> None:
        for status in ("Open", "Working", "Pending Review"):
            self.assertTrue(is_idea_card(self._card(status)), status)
        for status in ("Completed", "Cancelled"):
            self.assertFalse(is_idea_card(self._card(status)), status)

    def test_a_vietnamese_board_closes_its_cards_too(self) -> None:
        # Bot chạy trên *bất kỳ* board nào nó được thêm vào, và app này nói
        # tiếng Việt — một board đặt cột là "Đã hủy" hoàn toàn có thật. So
        # nguyên văn chữ tiếng Anh thì thẻ người ta đã huỷ vẫn được đếm là
        # việc đang chờ, và bot đốt quota tạo ảnh cho nó.
        for status in ("Đã hủy", "Huỷ bỏ", "Hoàn thành", "Đã đóng"):
            self.assertFalse(is_idea_card(self._card(status)), status)
        for status in ("Chờ duyệt", "Đang làm", "Mới"):
            self.assertTrue(is_idea_card(self._card(status)), status)

    def test_the_d_with_stroke_is_folded_before_accents_are_stripped(self) -> None:
        # ``đ`` là một chữ cái riêng, không phải ``d`` cộng dấu, nên
        # ``unicodedata`` không tách được nó. Không gấp nó lại trước thì
        # "Đã hủy" nén thành "ahuy" và bảng ở trên phải viết đúng chuỗi trông
        # như gõ nhầm ấy mới khớp.
        self.assertEqual("dahuy", compact_status("Đã hủy"))
        self.assertEqual("dahuy", compact_status("  ĐÃ HỦY  "))
        self.assertEqual("pendingreview", compact_status("Pending Review"))
        self.assertEqual("", compact_status(None))


class IdentityTests(unittest.TestCase):
    """How the bot learns which ERP user it is."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_it_reads_its_own_identity_off_a_comment_marked_mine(self) -> None:
        # Free, and it avoids writing a probe comment onto somebody's card.
        client = FakeClient([], {}, {})
        config = AgentBotConfig(token="t0ken")
        bot = AgentBot(config, client=client, state=AgentBotState.load(self.tmp / "s.json"))
        trees = [{"root": task_node("TASK-1", comments=[comment("c1", mine=1)])}]
        self.assertEqual(BOT, bot.resolve_bot_user(trees))

    def test_a_card_with_only_other_peoples_comments_teaches_it_nothing(self) -> None:
        client = FakeClient([], {}, {})
        bot = AgentBot(AgentBotConfig(token="t0ken"), client=client, state=AgentBotState.load(self.tmp / "s.json"))
        trees = [{"root": task_node("TASK-1", comments=[comment("c1", mine=0, owner="phong@havigroup.llc")])}]
        self.assertEqual("", bot.resolve_bot_user(trees))

    def test_the_write_probe_cleans_up_after_itself(self) -> None:
        class ProbeClient(FakeClient):
            def task_full(self, name: str, depth: int = 1) -> Dict[str, Any]:
                posted = self.comments[-1][1]
                return {"root": task_node(name, comments=[comment("probe", mine=1, content=posted, attachments=[])])}

        client = ProbeClient([], {}, {})
        bot = AgentBot(AgentBotConfig(token="t0ken"), client=client, state=AgentBotState.load(self.tmp / "s.json"))
        self.assertEqual(BOT, bot.probe_bot_user("TASK-1"))
        self.assertEqual([("TASK-1", "probe")], client.deleted)


class StateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_a_corrupt_state_file_starts_empty_rather_than_crashing(self) -> None:
        path = self.tmp / "state.json"
        path.write_text("{ not json", encoding="utf-8")
        state = AgentBotState.load(path)
        self.assertEqual({}, state.handled)

    def test_old_decisions_are_pruned_but_recent_ones_are_not(self) -> None:
        state = AgentBotState(path=self.tmp / "state.json")
        old = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat(timespec="seconds")
        state.handled = {
            "old": {"task": "T", "decision": "keep", "at": old},
            "new": {"task": "T", "decision": "keep", "at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        }
        state.prune()
        self.assertEqual(["new"], sorted(state.handled))

    def test_saving_leaves_no_half_written_file_behind(self) -> None:
        state = AgentBotState(path=self.tmp / "state.json")
        state.record("c1", "TASK-1", "keep")
        state.save()
        self.assertEqual("c1", next(iter(json.loads(state.path.read_text(encoding="utf-8"))["handled"])))
        self.assertFalse(state.path.with_suffix(".tmp").exists())


class RateLimitTests(unittest.TestCase):
    def test_it_blocks_once_the_window_is_full(self) -> None:
        # The bot ceiling is 60/minute; going over turns a scan into a 429.
        limiter = _RateLimiter(limit=2, window_s=0.3)
        started = time.monotonic()
        for _ in range(3):
            limiter.acquire()
        self.assertGreaterEqual(time.monotonic() - started, 0.25)


class ConfigTests(unittest.TestCase):
    def test_the_project_list_accepts_commas_semicolons_and_stray_spaces(self) -> None:
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"ERP_AGENT_TOKEN": "t", "ERP_AGENT_PROJECTS": " proj-0013 ; PROJ-0049,"}):
            config = AgentBotConfig.from_env()
        self.assertEqual(("PROJ-0013", "PROJ-0049"), config.projects)
        self.assertTrue(config.enabled)

    def test_narrowing_the_scope_still_keeps_the_project_the_app_lives_in(self) -> None:
        # Otherwise "add PROJ-0013 to the bot" would quietly take the bot off
        # the board the rest of Flow v2 is already pointed at.
        import os
        from unittest.mock import patch

        env = {"ERP_AGENT_TOKEN": "t", "ERP_AGENT_PROJECTS": "PROJ-0013", "ERP_PROJECT_ID": "PROJ-0049"}
        with patch.dict(os.environ, env):
            self.assertEqual(("PROJ-0013", "PROJ-0049"), AgentBotConfig.from_env().projects)

    def test_an_empty_project_list_still_means_every_visible_project(self) -> None:
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"ERP_AGENT_TOKEN": "t", "ERP_AGENT_PROJECTS": "", "ERP_PROJECT_ID": "PROJ-0049"}):
            self.assertEqual((), AgentBotConfig.from_env().projects)

    def test_board_is_the_default_scope_and_card_is_opt_in(self) -> None:
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"ERP_AGENT_TOKEN": "t", "ERP_AGENT_SCOPE": ""}):
            self.assertEqual("board", AgentBotConfig.from_env().scope)
        with patch.dict(os.environ, {"ERP_AGENT_TOKEN": "t", "ERP_AGENT_SCOPE": " Card "}):
            self.assertEqual("card", AgentBotConfig.from_env().scope)
        # Một giá trị gõ sai không được âm thầm tắt bot khỏi cả board.
        with patch.dict(os.environ, {"ERP_AGENT_TOKEN": "t", "ERP_AGENT_SCOPE": "cards"}):
            self.assertEqual("board", AgentBotConfig.from_env().scope)

    def test_an_empty_token_leaves_the_bot_off(self) -> None:
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"ERP_AGENT_TOKEN": "  "}):
            self.assertFalse(AgentBotConfig.from_env().enabled)


if __name__ == "__main__":
    unittest.main()

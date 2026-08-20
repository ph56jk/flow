"""Reading the ERP Task's own metadata — the block that says what a Task *is*.

This repo's agent works image cards; the listing half of the family works Etsy
cards.  Both live in the same ERP and are told apart by one thing: the
*Thuộc tính* panel block that ``flow_web.erp_meta`` parses::

    action_1: listing
    acc: acc32

An image card writes no ``action_*`` at all, so "said nothing" has to keep
meaning *carry on as before* — never *reject*.  That asymmetry is the reason
this file exists here and not only in the listing repo: it is what lets one
agent hold both kinds of card without either half stepping on the other.

The parser half of the listing repo's ``tests/test_erp_task_meta.py``, carried
over unchanged.  The half that exercises ``FlowWebService`` did not come with
it — this repo has no Etsy service to exercise yet.
"""

from __future__ import annotations

import unittest

from flow_web.erp_meta import (
    LISTING_ACTIONS,
    TaskMeta,
    agent_users,
    inherit,
    machine_for_account,
    parent_task_id,
    normalize_action,
    parse_meta_block,
    resolve_routing,
    task_meta,
)

from flow_web.store import StateStore


class ParseMetaBlockTests(unittest.TestCase):
    def test_reads_the_panel_block_as_the_panel_writes_it(self) -> None:
        parsed = parse_meta_block("action_1: listing\nacc: acc32\n")

        self.assertEqual({"action_1": "listing", "acc": "acc32"}, parsed)

    def test_a_broken_line_is_skipped_instead_of_taking_the_sweep_down(self) -> None:
        parsed = parse_meta_block(
            "\n".join(
                [
                    "# ghi chú",
                    "acc: acc32",
                    "khong-co-dau-hai-cham",
                    "Không Hợp Lệ: x",
                    "- listing",
                    "",
                    "action: listing",
                ]
            )
        )

        self.assertEqual({"acc": "acc32", "action": "listing"}, parsed)

    def test_quotes_lists_and_nulls_flatten_to_plain_text(self) -> None:
        parsed = parse_meta_block(
            "\n".join(
                [
                    'acc: "acc32"',
                    "_labels: [urgent, etsy]",
                    "note: null",
                    "empty: ~",
                ]
            )
        )

        self.assertEqual("acc32", parsed["acc"])
        self.assertEqual("urgent, etsy", parsed["_labels"])
        self.assertEqual("", parsed["note"])
        self.assertEqual("", parsed["empty"])

    def test_a_repeated_key_keeps_the_last_value(self) -> None:
        self.assertEqual({"acc": "acc16"}, parse_meta_block("acc: acc32\nacc: acc16"))


class TaskMetaTests(unittest.TestCase):
    def test_actions_come_back_in_panel_order(self) -> None:
        meta = TaskMeta(attributes=parse_meta_block("action_2: review\naction_1: listing\naction: check"))

        self.assertEqual(["check", "listing", "review"], meta.actions)

    def test_one_key_may_hold_several_actions(self) -> None:
        meta = TaskMeta(attributes=parse_meta_block("action_1: Listing Etsy, review"))

        self.assertEqual(["listing_etsy", "review"], meta.actions)
        self.assertTrue(meta.is_listing)

    def test_a_task_that_names_no_action_declares_nothing(self) -> None:
        meta = TaskMeta(attributes=parse_meta_block("acc: acc32"))

        self.assertFalse(meta.declares_actions)
        self.assertFalse(meta.is_listing)
        self.assertEqual("acc32", meta.account_id)

    def test_account_is_read_from_any_of_the_accepted_keys(self) -> None:
        self.assertEqual("acc32", TaskMeta(attributes={"account": "ACC32"}).account_id)
        self.assertEqual("acc32", TaskMeta(attributes={"etsy_account": " acc32 "}).account_id)
        # "default"/"auto" mean "nothing was said", not an account named that.
        self.assertEqual("", TaskMeta(attributes={"acc": "default"}).account_id)

    def test_it_reads_a_task_detail_or_the_card_built_from_one(self) -> None:
        detail = {"name": "TASK-2026-01148", "meta": "acc: acc32", "meta_auto": "_status: Open"}

        self.assertEqual("acc32", task_meta(detail).account_id)
        self.assertEqual("acc32", task_meta({"id": "TASK-2026-01148", "_erp_raw": detail}).account_id)
        self.assertEqual("Open", task_meta(detail).get("_status"))

    def test_a_task_with_no_metadata_at_all_is_silent_not_an_error(self) -> None:
        meta = task_meta({"id": "TASK-2026-01148"})

        self.assertEqual([], meta.actions)
        self.assertEqual("", meta.account_id)
        self.assertEqual("", meta.machine_id)


class AssignedAgentTests(unittest.TestCase):
    """The other half of the family routes by the assigned bot, so we read it too."""

    def test_the_assignment_comes_from_the_task_detail(self) -> None:
        meta = task_meta(
            {
                "id": "TASK-2026-01148",
                "agents": [{"bot_user": "flow-bot@havigroup.llc"}, {"bot_user": "listing-bot@havigroup.llc"}],
            }
        )

        self.assertEqual(("flow-bot@havigroup.llc", "listing-bot@havigroup.llc"), meta.agent_users)
        self.assertTrue(meta.assigned_to("Flow-Bot@havigroup.llc"))
        self.assertFalse(meta.assigned_to("someone-else@havigroup.llc"))

    def test_the_rendered_line_is_used_when_the_detail_carries_no_agent_list(self) -> None:
        meta = task_meta({"meta_auto": "_agents: flow-bot@havigroup.llc, listing-bot@havigroup.llc"})

        self.assertEqual(("flow-bot@havigroup.llc", "listing-bot@havigroup.llc"), meta.agent_users)

    def test_the_real_field_beats_the_rendered_line(self) -> None:
        meta = task_meta(
            {
                "meta_auto": "_agents: stale-bot@havigroup.llc",
                "agents": [{"bot_user": "flow-bot@havigroup.llc"}],
            }
        )

        self.assertEqual(("flow-bot@havigroup.llc",), meta.agent_users)

    def test_an_unassigned_task_answers_no_to_everyone(self) -> None:
        meta = task_meta({"id": "TASK-2026-01148"})

        self.assertEqual((), meta.agent_users)
        self.assertFalse(meta.assigned_to("flow-bot@havigroup.llc"))
        self.assertFalse(meta.assigned_to(""))

    def test_a_duplicated_or_empty_assignment_does_not_produce_a_phantom_bot(self) -> None:
        self.assertEqual(
            ("flow-bot@havigroup.llc",),
            agent_users({"agents": [{"bot_user": "flow-bot@havigroup.llc"}, {"bot_user": " "}, {"bot_user": "flow-bot@havigroup.llc"}]}),
        )
        self.assertEqual((), agent_users(None))


class FlowProfileTests(unittest.TestCase):
    """``profile:`` names a Google Flow browser profile, not an Etsy account."""

    def test_the_profile_label_is_kept_exactly_as_written(self) -> None:
        meta = task_meta({"meta": "profile: Acc 32 Flow\nacc: acc32"})

        self.assertEqual("Acc 32 Flow", meta.flow_profile)
        self.assertEqual("acc32", meta.account_id)

    def test_a_profile_named_default_survives(self) -> None:
        self.assertEqual("default", task_meta({"meta": "flow_profile: default"}).flow_profile)

    def test_an_account_alone_says_nothing_about_the_flow_profile(self) -> None:
        self.assertEqual("", task_meta({"meta": "acc: acc32"}).flow_profile)


class MachineForAccountTests(unittest.TestCase):
    FLEET = ("etsy-vn32", "etsy-16", "capa-hinh")

    def test_the_fleet_number_is_what_an_operator_means_by_acc32(self) -> None:
        self.assertEqual("etsy-vn32", machine_for_account("acc32", self.FLEET))
        self.assertEqual("etsy-16", machine_for_account("acc16", self.FLEET))

    def test_an_account_named_exactly_like_a_machine_matches_first(self) -> None:
        self.assertEqual("etsy-16", machine_for_account("etsy-16", self.FLEET))

    def test_an_ambiguous_number_resolves_to_nothing_rather_than_a_guess(self) -> None:
        self.assertEqual("", machine_for_account("acc32", ("etsy-vn32", "etsy-32")))

    def test_an_account_with_no_number_and_no_match_resolves_to_nothing(self) -> None:
        self.assertEqual("", machine_for_account("shop-noel", self.FLEET))
        self.assertEqual("", machine_for_account("", self.FLEET))


class ResolveRoutingTests(unittest.TestCase):
    FLEET = ("etsy-vn32", "etsy-16")

    def test_a_machine_written_on_the_task_beats_every_other_source(self) -> None:
        meta = TaskMeta(attributes=parse_meta_block("acc: acc32\nmachine: capa-hinh"))

        routing = resolve_routing(
            meta,
            known_machines=self.FLEET,
            account_machines={"acc32": "etsy-vn32"},
        )

        self.assertEqual("acc32", routing.account_id)
        self.assertEqual("capa-hinh", routing.machine_id)
        self.assertEqual("meta_machine", routing.machine_source)

    def test_the_configured_machine_beats_the_naming_convention(self) -> None:
        routing = resolve_routing(
            TaskMeta(attributes={"acc": "acc32"}),
            known_machines=self.FLEET,
            account_machines={"acc32": "etsy-16"},
        )

        self.assertEqual("etsy-16", routing.machine_id)
        self.assertEqual("account_config", routing.machine_source)

    def test_with_nothing_configured_the_fleet_number_decides(self) -> None:
        routing = resolve_routing(TaskMeta(attributes={"acc": "acc32"}), known_machines=self.FLEET)

        self.assertEqual("etsy-vn32", routing.machine_id)
        self.assertEqual("fleet_number", routing.machine_source)
        self.assertEqual("meta_acc", routing.account_source)

    def test_an_account_with_no_machine_anywhere_stays_claimable_by_any_machine(self) -> None:
        routing = resolve_routing(TaskMeta(attributes={"acc": "shop-noel"}), known_machines=self.FLEET)

        self.assertEqual("shop-noel", routing.account_id)
        self.assertEqual("", routing.machine_id)
        self.assertFalse(routing.known_account)

    def test_a_registered_account_is_reported_as_known(self) -> None:
        routing = resolve_routing(
            TaskMeta(attributes={"acc": "acc32"}),
            known_accounts=("acc32", "acc16"),
            known_machines=self.FLEET,
        )

        self.assertTrue(routing.known_account)

    def test_a_task_that_says_nothing_routes_nowhere(self) -> None:
        routing = resolve_routing(TaskMeta(), known_machines=self.FLEET)

        self.assertFalse(routing.resolved)
        self.assertEqual("", routing.account_id)


class InheritedMetaTests(unittest.TestCase):
    """ERP hands nothing down by itself, so the reader does it."""

    def test_the_parent_is_found_under_any_of_the_spellings(self) -> None:
        self.assertEqual("TASK-2026-01000", parent_task_id({"parent_task": "TASK-2026-01000"}))
        self.assertEqual("TASK-2026-01000", parent_task_id({"parentTask": "TASK-2026-01000"}))
        self.assertEqual("TASK-2026-01000", parent_task_id({"parent": {"name": "TASK-2026-01000"}}))
        self.assertEqual("", parent_task_id({"parent_task": "None"}))
        self.assertEqual("", parent_task_id(None))

    def test_the_child_takes_what_it_did_not_write_itself(self) -> None:
        parent = task_meta({"meta": "action_1: listing\nacc: acc32"})
        child = task_meta({"meta": "note: mau do"})

        merged = inherit(child, parent)

        self.assertEqual("acc32", merged.account_id)
        self.assertTrue(merged.is_listing)
        self.assertEqual("mau do", merged.get("note"))

    def test_a_line_the_child_wrote_beats_the_parent(self) -> None:
        parent = task_meta({"meta": "acc: acc32\nmachine: etsy-vn32"})
        child = task_meta({"meta": "acc: acc16"})

        merged = inherit(child, parent)

        self.assertEqual("acc16", merged.account_id)
        self.assertEqual("etsy-vn32", merged.machine_id)

    def test_meta_auto_is_never_inherited(self) -> None:
        parent = task_meta({"meta_auto": "_task: TASK-2026-01000\n_status: Completed"})
        child = task_meta({"meta_auto": "_task: TASK-2026-01148\n_status: Open", "meta": "acc: acc32"})

        merged = inherit(child, parent)

        self.assertEqual("TASK-2026-01148", merged.auto.get("_task"))
        self.assertEqual("Open", merged.auto.get("_status"))

    def test_agents_come_down_only_when_the_child_has_none(self) -> None:
        parent = task_meta({"agents": [{"bot_user": "flow-bot@havigroup.llc"}]})

        self.assertEqual(("flow-bot@havigroup.llc",), inherit(task_meta({}), parent).agent_users)
        self.assertEqual(
            ("listing-bot@havigroup.llc",),
            inherit(task_meta({"agents": [{"bot_user": "listing-bot@havigroup.llc"}]}), parent).agent_users,
        )

    def test_a_task_with_no_parent_is_returned_untouched(self) -> None:
        child = task_meta({"meta": "acc: acc32"})

        self.assertIs(child, inherit(child, None))
        self.assertIs(child, inherit(child, TaskMeta()))


class OneAgentTwoKindsOfCardTests(unittest.TestCase):
    """The dispatch this repo needs: image card or listing card, from ``meta``.

    Both shapes below are copied off real cards, not invented.  The image card
    is what the *Thuộc tính* panel holds on an idea card in this repo; the
    listing card is what the Etsy half writes.
    """

    IMAGE_CARD = {"meta": "sku:\nproduct: khan tay\nfatheridea:\n"}
    LISTING_CARD = {"meta": "action_1: listing\nacc: acc32\n"}

    def test_an_image_card_is_not_mistaken_for_a_listing(self) -> None:
        meta = task_meta(self.IMAGE_CARD)

        self.assertFalse(meta.is_listing)
        self.assertEqual([], meta.actions)
        self.assertEqual("khan tay", meta.get("product"))

    def test_an_image_card_declares_nothing_so_it_keeps_its_old_behaviour(self) -> None:
        # The whole safety of putting both halves on one agent rests here: a
        # card that names no action must read as "carry on", never as "reject".
        self.assertFalse(task_meta(self.IMAGE_CARD).declares_actions)

    def test_a_listing_card_is_recognised_and_names_its_account(self) -> None:
        meta = task_meta(self.LISTING_CARD)

        self.assertTrue(meta.is_listing)
        self.assertEqual("acc32", meta.account_id)

    def test_every_spelling_the_panel_has_used_for_listing_is_recognised(self) -> None:
        for spelling in ("listing", "Listing Etsy", "listing-etsy", "dang listing", "LEN_LISTING"):
            with self.subTest(spelling=spelling):
                self.assertTrue(task_meta({"meta": f"action_1: {spelling}"}).is_listing)

    def test_normalising_is_what_makes_those_spellings_meet(self) -> None:
        self.assertEqual("etsy_listing", normalize_action("Etsy Listing"))
        self.assertEqual("etsy_listing", normalize_action(" etsy-listing "))
        self.assertIn(normalize_action("Listing"), LISTING_ACTIONS)

    def test_a_card_asking_for_other_work_is_not_a_listing_but_still_speaks(self) -> None:
        meta = task_meta({"meta": "action_1: watermark"})

        self.assertFalse(meta.is_listing)
        self.assertTrue(meta.declares_actions)

    def test_a_listing_child_of_an_image_parent_keeps_its_own_action(self) -> None:
        merged = inherit(task_meta(self.LISTING_CARD), task_meta(self.IMAGE_CARD))

        self.assertTrue(merged.is_listing)
        self.assertEqual("khan tay", merged.get("product"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

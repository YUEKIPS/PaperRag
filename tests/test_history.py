"""History selection and stub contextualize. No index and no live LLM."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.agent.history import (  # noqa: E402
    DEFAULT_MAX_HISTORY_BYTES,
    DEFAULT_MAX_TURNS,
    HistoryTurn,
    contextualize_query,
    format_history_block,
    policy_label,
    prior_conversation_from_turns,
    select_history,
    stub_contextualize,
)
from src.agent.nodes import decide_node, generate_node, retrieve_node, rewrite_node  # noqa: E402
from src.agent.run import run_agentic_query  # noqa: E402
from src.generate.baseline import build_generate_user_message  # noqa: E402
from src.retriever.baseline import RetrievedChunk  # noqa: E402

_STUB_ENV = {"AGENT_GENERATOR": "stub", "BASELINE_GENERATOR": "stub"}


def _turn(n: int, answer_bytes: int = 8) -> dict[str, str]:
    answer = ("a" * answer_bytes) if answer_bytes else "x"
    return {"question": f"q{n}", "answer": answer}


class SelectHistoryTests(unittest.TestCase):
    def test_empty_and_short_history(self) -> None:
        empty = select_history([])
        self.assertEqual(empty.included_turns, 0)
        self.assertEqual(empty.omitted_turns, 0)
        self.assertEqual(empty.policy, policy_label(DEFAULT_MAX_TURNS, DEFAULT_MAX_HISTORY_BYTES))

        three = select_history([_turn(i) for i in range(3)])
        self.assertEqual(three.included_turns, 3)
        self.assertEqual(three.omitted_turns, 0)
        self.assertEqual([t.question for t in three.turns], ["q0", "q1", "q2"])

    def test_keeps_last_six_complete_turns(self) -> None:
        selected = select_history([_turn(i) for i in range(8)])
        self.assertEqual(selected.included_turns, 6)
        self.assertEqual(selected.omitted_turns, 2)
        self.assertEqual([t.question for t in selected.turns], ["q2", "q3", "q4", "q5", "q6", "q7"])
        self.assertEqual(selected.truncated_answers, 0)

    def test_incomplete_turns_are_not_omitted_counts(self) -> None:
        conversation = [
            {"question": "kept-a", "answer": "yes"},
            {"question": "no-answer", "answer": "  "},
            {"question": "", "answer": "no-question"},
            {"question": "kept-b", "answer": "yes"},
        ]
        selected = select_history(conversation)
        self.assertEqual([t.question for t in selected.turns], ["kept-a", "kept-b"])
        self.assertEqual(selected.omitted_turns, 0)
        self.assertEqual(selected.included_turns, 2)

    def test_drops_whole_older_turns_before_truncating(self) -> None:
        conversation = [
            {"question": "old", "answer": "o" * 80},
            {"question": "new", "answer": "n" * 80},
        ]
        selected = select_history(conversation, max_turns=6, max_history_bytes=100)
        self.assertEqual(selected.included_turns, 1)
        self.assertEqual(selected.omitted_turns, 1)
        self.assertEqual(selected.truncated_answers, 0)
        self.assertEqual(selected.turns[0].question, "new")
        self.assertEqual(selected.turns[0].answer, "n" * 80)
        self.assertLessEqual(selected.history_bytes, 100)

    def test_byte_budget_and_turn_cap_both_count_as_omitted(self) -> None:
        conversation = [_turn(i, answer_bytes=90) for i in range(10)]
        selected = select_history(conversation, max_turns=6, max_history_bytes=250)
        self.assertEqual(selected.included_turns, 2)
        self.assertEqual(selected.omitted_turns, 8)
        self.assertEqual([t.question for t in selected.turns], ["q8", "q9"])
        self.assertLessEqual(selected.history_bytes, 250)
        self.assertEqual(selected.truncated_answers, 0)

    def test_truncates_newest_answer_when_it_alone_exceeds_budget(self) -> None:
        conversation = [
            {"question": "small", "answer": "ok"},
            {"question": "Q", "answer": "汉" * 40},
        ]
        # "汉" is 3 bytes; 40 * 3 + len("Q") = 121.
        selected = select_history(conversation, max_turns=6, max_history_bytes=40)
        self.assertEqual(selected.included_turns, 1)
        self.assertEqual(selected.omitted_turns, 1)
        self.assertEqual(selected.truncated_answers, 1)
        self.assertEqual(selected.turns[0].question, "Q")
        self.assertNotEqual(selected.turns[0].answer, "汉" * 40)
        self.assertTrue(selected.turns[0].answer.endswith("…"))
        self.assertLessEqual(selected.history_bytes, 40)
        self.assertNotIn("small", selected.turns[0].question)

    def test_utf8_budget_not_character_budget(self) -> None:
        question = "你" * 10  # 30 bytes
        answer = "好"  # 3 bytes
        selected = select_history(
            [{"question": question, "answer": answer}],
            max_turns=6,
            max_history_bytes=33,
        )
        self.assertEqual(selected.included_turns, 1)
        self.assertEqual(selected.truncated_answers, 0)
        self.assertEqual(selected.history_bytes, 33)

        tight = select_history(
            [{"question": question, "answer": answer}],
            max_turns=6,
            max_history_bytes=32,
        )
        self.assertEqual(tight.truncated_answers, 1)
        self.assertLessEqual(tight.history_bytes, 32)
        self.assertEqual(tight.turns[0].question, question)

    def test_config_overrides_defaults(self) -> None:
        config = {"agent": {"conversation": {"max_turns": 2, "max_history_bytes": 24000}}}
        selected = select_history([_turn(i) for i in range(5)], config=config)
        self.assertEqual(selected.included_turns, 2)
        self.assertEqual(selected.omitted_turns, 3)
        self.assertEqual(selected.policy, "last_2_turns_and_24000_utf8_bytes")

    def test_explicit_args_override_config(self) -> None:
        config = {"agent": {"conversation": {"max_turns": 2, "max_history_bytes": 10}}}
        selected = select_history([_turn(i, answer_bytes=1) for i in range(4)], config=config, max_turns=3)
        self.assertEqual(selected.included_turns, 3)
        self.assertEqual(selected.policy, "last_3_turns_and_10_utf8_bytes")


class ContextualizeTests(unittest.TestCase):
    def test_stub_followups_become_standalone(self) -> None:
        turns = [HistoryTurn("ReAct 的核心思想是什么？", "推理与行动交替。")]
        method = stub_contextualize("它的方法呢", turns)
        self.assertEqual(method, "ReAct 的核心思想是什么？ — 它的方法呢")
        point = stub_contextualize("第二点展开", [HistoryTurn("RAG 有哪些组件？", "1. 检索 2. 生成")])
        self.assertEqual(point, "RAG 有哪些组件？ — 第二点展开")

    def test_stub_leaves_standalone_questions(self) -> None:
        turns = [HistoryTurn("ReAct 的核心思想是什么？", "交替。")]
        query = "BM25 和向量检索如何融合？"
        self.assertEqual(stub_contextualize(query, turns), query)
        self.assertEqual(stub_contextualize("它的方法呢", []), "它的方法呢")

    def test_decide_uses_stub_without_calling_llm(self) -> None:
        state = {
            "query": "它的方法呢",
            "config": {},
            "conversation": [{"question": "ReAct 的核心思想是什么？", "answer": "交替推理与行动。"}],
            "history_included_turns": 1,
            "history_omitted_turns": 0,
            "history_policy": policy_label(6, 24000),
            "trace": [],
        }
        with patch.dict(os.environ, _STUB_ENV, clear=False):
            with patch("src.agent.history.try_openai_chat") as mocked:
                out = decide_node(state)
        mocked.assert_not_called()
        self.assertEqual(out["working_query"], "ReAct 的核心思想是什么？ — 它的方法呢")
        event = out["trace"][-1]
        self.assertEqual(event["event"], "decide")
        self.assertEqual(event["contextualize_backend"], "stub")
        self.assertTrue(event["contextualized"])
        self.assertEqual(event["history_omitted_turns"], 0)

    def test_llm_contextualize_is_mocked(self) -> None:
        turns = [HistoryTurn("ReAct 的核心思想是什么？", "交替推理与行动。")]

        def fake(messages, **kwargs):
            self.assertIn("standalone", messages[0]["content"].lower())
            self.assertIn("它的方法呢", messages[1]["content"])
            self.assertIn("NOT evidence", messages[1]["content"])
            return "ReAct 的方法是什么？", None

        with patch.dict(os.environ, {"AGENT_GENERATOR": "openai", "BASELINE_GENERATOR": "stub"}, clear=False):
            with patch("src.agent.history.try_openai_chat", fake):
                result = contextualize_query("它的方法呢", turns, config={})
        self.assertEqual(result.backend, "llm")
        self.assertEqual(result.working_query, "ReAct 的方法是什么？")
        self.assertTrue(result.changed)

    def test_llm_failure_falls_back_to_stub(self) -> None:
        turns = [HistoryTurn("ReAct 的核心思想是什么？", "交替。")]
        with patch.dict(os.environ, {"AGENT_GENERATOR": "openai"}, clear=False):
            with patch("src.agent.history.try_openai_chat", return_value=(None, "boom")):
                result = contextualize_query("它的方法呢", turns, config={})
        self.assertEqual(result.backend, "stub")
        self.assertEqual(result.llm_fallback, "boom")
        self.assertIn("ReAct", result.working_query)


class RewriteAndGenerateTests(unittest.TestCase):
    def test_stub_rewrite_keeps_resolved_query(self) -> None:
        state = {
            "query": "它的方法呢",
            "working_query": "ReAct 的核心思想是什么？ — 它的方法呢",
            "grade_reason": "stub_overlap_low",
            "iterations": 0,
            "config": {},
            "conversation": [
                {"question": "ReAct 的核心思想是什么？", "answer": "推理与行动交替。"}
            ],
            "trace": [],
        }
        with patch.dict(os.environ, _STUB_ENV, clear=False):
            with patch("src.agent.nodes.try_openai_chat") as mocked:
                out = rewrite_node(state)
        mocked.assert_not_called()
        self.assertIn("ReAct 的核心思想是什么？", out["working_query"])
        self.assertIn("它的方法呢", out["working_query"])
        self.assertEqual(out["trace"][-1]["backend"], "stub")

    def test_retrieve_uses_working_query_only(self) -> None:
        captured: dict[str, str] = {}

        def fake_retrieve(query, index_dir, config, rerank_override=None):
            captured["query"] = query
            return []

        state = {
            "query": "它的方法呢",
            "working_query": "ReAct method",
            "index_dir": "/tmp",
            "config": {"agent": {}, "retriever": {"top_k": 3}},
            "conversation": [
                {"question": "ReAct?", "answer": "past answer cites 9999.99999 p.1"}
            ],
            "trace": [],
        }
        with patch("src.agent.nodes.retrieve_with_config", fake_retrieve):
            out = retrieve_node(state)
        self.assertEqual(captured["query"], "ReAct method")
        self.assertEqual(out["chunks"], [])
        self.assertNotIn("9999.99999", out["trace"][-1]["working_query"])

    def test_generate_message_marks_history_as_reference_only(self) -> None:
        history = format_history_block([HistoryTurn("ReAct?", "PAST_ANSWER_SECRET cites 9999.99999")])
        message = build_generate_user_message(
            "它的方法呢",
            "(1) [2005.11401 p.3] CURRENT_CHUNK",
            history,
        )
        self.assertIn("PAST_ANSWER_SECRET", message)
        self.assertIn("CURRENT_CHUNK", message)
        self.assertLess(message.index("PAST_ANSWER_SECRET"), message.index("CURRENT_CHUNK"))
        self.assertIn("not evidence", message.lower())
        self.assertIn("Conclusions and citations must come only from this turn", message)

    def test_stub_generate_cites_only_current_chunks(self) -> None:
        chunk = RetrievedChunk(
            paper_id="2005.11401",
            page_number=3,
            chunk_id="c1",
            text="CURRENT_CHUNK_TEXT",
            score=0.9,
        )
        state = {
            "query": "它的方法呢",
            "working_query": "ReAct — 它的方法呢",
            "chunks": [chunk],
            "config": {},
            "conversation": [{"question": "ReAct?", "answer": "PAST_ONLY_MARKER cites 9999.99999"}],
            "trace": [],
        }
        with patch.dict(os.environ, _STUB_ENV, clear=False):
            out = generate_node(state)
        self.assertEqual(
            out["citations"],
            [{"paper_id": "2005.11401", "page": 3, "chunk_id": "c1"}],
        )
        self.assertIn("CURRENT_CHUNK_TEXT", out["answer"])
        self.assertNotIn("PAST_ONLY_MARKER", out["answer"])
        self.assertNotIn("9999.99999", out["answer"])

    def test_prior_payload_drops_citations(self) -> None:
        payload = prior_conversation_from_turns(
            [
                {
                    "query": "什么是 RAG？",
                    "result": {
                        "answer": "检索增强生成。",
                        "citations": [{"paper_id": "2005.11401", "page": 2}],
                    },
                }
            ]
        )
        self.assertEqual(payload, [{"question": "什么是 RAG？", "answer": "检索增强生成。"}])
        self.assertNotIn("citations", payload[0])


class RunWiringTests(unittest.TestCase):
    def test_run_passes_selected_history_without_graph_io(self) -> None:
        captured: dict[str, object] = {}

        class FakeApp:
            def invoke(self, initial):
                captured["initial"] = initial
                return {
                    "working_query": "standalone",
                    "answer": "ok",
                    "citations": [],
                    "generator": "stub",
                    "grade_passed": True,
                    "grade_reason": "",
                    "iterations": 0,
                    "trace": [],
                    "chunks": [],
                    "history_included_turns": initial["history_included_turns"],
                    "history_omitted_turns": initial["history_omitted_turns"],
                    "history_policy": initial["history_policy"],
                    "history_truncated_answers": initial["history_truncated_answers"],
                }

        conversation = [_turn(i) for i in range(8)]
        with patch("src.agent.run.build_agent_graph", return_value=FakeApp()):
            result = run_agentic_query("追问", Path("/tmp"), {}, conversation=conversation)
        initial = captured["initial"]
        assert isinstance(initial, dict)
        self.assertEqual(len(initial["conversation"]), 6)
        self.assertEqual(initial["conversation"][0]["question"], "q2")
        self.assertEqual(initial["conversation"][-1]["question"], "q7")
        self.assertEqual(result.history_included_turns, 6)
        self.assertEqual(result.history_omitted_turns, 2)
        self.assertEqual(result.history_policy, policy_label(6, 24000))
        self.assertEqual(result.working_query, "standalone")

    def test_real_graph_retrieves_rewritten_query_not_past_answers(self) -> None:
        chunk = RetrievedChunk(
            paper_id="2005.11401",
            page_number=4,
            chunk_id="c9",
            text="CURRENT_ONLY",
            score=1.0,
        )
        queries: list[str] = []

        def fake_retrieve(query, index_dir, config, rerank_override=None):
            queries.append(query)
            return [chunk]

        conversation = [
            {"question": "ReAct 的核心思想是什么？", "answer": "PAST_MARKER cites 9999.99999"},
            {"question": "  ", "answer": "incomplete"},
        ]
        config = {
            "agent": {"max_grade_rewrite_loops": 1, "max_context_chunks": 5},
            "retriever": {"top_k": 3},
        }
        with patch.dict(os.environ, _STUB_ENV, clear=False):
            with patch("src.agent.nodes.retrieve_with_config", fake_retrieve):
                result = run_agentic_query(
                    "它的方法呢",
                    Path("/tmp/no-index"),
                    config,
                    conversation=conversation,
                )
        self.assertTrue(queries)
        self.assertEqual(queries[0], "ReAct 的核心思想是什么？ — 它的方法呢")
        for query in queries:
            self.assertNotIn("PAST_MARKER", query)
            self.assertNotIn("9999.99999", query)
        self.assertEqual(result.history_included_turns, 1)
        self.assertEqual(result.history_omitted_turns, 0)
        self.assertEqual(result.citations[0]["chunk_id"], "c9")
        self.assertNotIn("PAST_MARKER", result.answer)
        self.assertIn("CURRENT_ONLY", result.answer)


if __name__ == "__main__":
    unittest.main()

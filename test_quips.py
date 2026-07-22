import unittest

from tokeneyes.vision import _fallback_quip, _is_boring_quip, QUIP_PROMPT


class QuipQualityTests(unittest.TestCase):
    def test_boring_quips_are_flagged(self):
        self.assertTrue(_is_boring_quip("That's 2.2M tokens. Write a novel!"))
        self.assertTrue(_is_boring_quip("You could generate a whole movie script."))
        self.assertTrue(_is_boring_quip("Chat with AI for a year."))

    def test_item_specific_quip_is_allowed(self):
        self.assertFalse(
            _is_boring_quip("This Apple Watch is 49.8M tokens of workflow damage.")
        )

    def test_new_crutches_are_flagged(self):
        self.assertTrue(_is_boring_quip("Time to touch grass after this purchase."))
        self.assertTrue(_is_boring_quip("Your wallet is crying right now."))
        self.assertTrue(_is_boring_quip("Imagine if you had saved that instead."))

    def test_fallback_quip_compares_against_a_concrete_work_unit(self):
        quip = _fallback_quip("Apple Watch SE (2nd generation)", 49_800_000, "Claude Sonnet 5")
        self.assertIn("Apple Watch", quip)
        # 49.8M / 180k ≈ 277 architecture docs — the largest unit that stays countable.
        self.assertIn("277 architecture docs", quip)
        self.assertNotIn("49,800,000", quip)

    def test_fallback_quip_scales_down_to_small_purchases(self):
        # Too small for a whole architecture doc, so it should drop to the next unit.
        quip = _fallback_quip("espresso", 140_000, "Claude Sonnet 5")
        self.assertIn("espresso", quip)
        self.assertIn("deep debug sessions", quip)

    def test_fallback_quip_uses_singular_when_it_lands_near_one_unit(self):
        quip = _fallback_quip("espresso", 200_000, "Claude Sonnet 5")
        self.assertIn("roughly one architecture doc", quip)

    def test_prompt_pushes_item_specific_roasts_without_locality_rule(self):
        self.assertIn("makes this exact purchase look ridiculous", QUIP_PROMPT)
        self.assertIn("only fits this purchase", QUIP_PROMPT)
        self.assertIn("write a novel", QUIP_PROMPT)
        self.assertNotIn("Avoid locality jokes", QUIP_PROMPT)

    def test_prompt_supplies_concrete_comparison_units(self):
        self.assertIn("A number by itself is not a joke.", QUIP_PROMPT)
        self.assertIn("PR review with full context", QUIP_PROMPT)


if __name__ == "__main__":
    unittest.main()

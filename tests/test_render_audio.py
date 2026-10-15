import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from render_video import _audio_encode_args


class NarrationMasteringTests(unittest.TestCase):
    def test_trivia_narration_has_controlled_loudness_and_sample_rate(self):
        self.assertEqual(_audio_encode_args({"category": "Geschichte"}),
                         ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000"])

    def test_missing_category_uses_normal_trivia_master(self):
        self.assertEqual(_audio_encode_args({}), _audio_encode_args({"category": "Natur"}))

    def test_shared_finance_contract_is_not_changed(self):
        self.assertEqual(_audio_encode_args({"category": "Finance"}), [])


if __name__ == "__main__":
    unittest.main()

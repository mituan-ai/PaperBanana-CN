import unittest

from utils.retrieval_settings import get_retrieval_setting_label


class RetrievalSettingLabelTest(unittest.TestCase):
    def test_labels_are_short_chinese_ui_labels(self):
        self.assertEqual(get_retrieval_setting_label("auto"), "智能检索（轻量）")
        self.assertEqual(get_retrieval_setting_label("auto-full"), "智能检索（高精度）")
        self.assertEqual(get_retrieval_setting_label("curated"), "固定参考集")
        self.assertEqual(get_retrieval_setting_label("random"), "随机参考样本")
        self.assertEqual(get_retrieval_setting_label("none"), "不使用参考")


if __name__ == "__main__":
    unittest.main()

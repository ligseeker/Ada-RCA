import inspect
from pathlib import Path
import unittest

from src.rca.supervised_baselines.common import (
    EXPECTED_CANDIDATES,
    load_label_subset,
    load_prediction_events,
    partition_fold,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SupervisedProtocolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = {
            dataset: load_prediction_events(PROJECT_ROOT, dataset)
            for dataset in ("re2ob", "re2tt")
        }

    def test_exact_existing_split_is_reused(self):
        for dataset, events in self.events.items():
            self.assertEqual(len(events), 90)
            observed_test_ids = set()
            for fold in (0, 1, 2):
                train, test = partition_fold(events, fold)
                self.assertEqual(len(train), 60)
                self.assertEqual(len(test), 30)
                self.assertFalse({row.case_id for row in train} & {row.case_id for row in test})
                observed_test_ids.update(row.case_id for row in test)
            self.assertEqual(observed_test_ids, set(events))

    def test_candidates_and_roots_are_complete(self):
        for dataset, events in self.events.items():
            ids = tuple(events)
            labels = load_label_subset(PROJECT_ROOT, dataset, ids)
            for case_id, event in events.items():
                self.assertEqual(len(event.candidates), EXPECTED_CANDIDATES[dataset])
                self.assertEqual(len(set(event.candidates)), len(event.candidates))
                self.assertEqual(event.candidates.count(labels[case_id]["root_service"]), 1)

    def test_prediction_event_is_physically_label_free(self):
        fields = set(inspect.signature(next(iter(self.events["re2ob"].values())).__class__).parameters)
        self.assertNotIn("root_service", fields)
        self.assertNotIn("fault_type", fields)


if __name__ == "__main__":
    unittest.main()

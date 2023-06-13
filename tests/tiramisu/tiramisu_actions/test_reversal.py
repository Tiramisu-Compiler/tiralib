from athena.tiramisu.schedule import Schedule
from athena.tiramisu.tiramisu_actions.reversal import Reversal
from athena.utils.config import BaseConfig
import tests.utils as test_utils


def test_reversal_init():
    reversal = Reversal(["i0"], ["comp00"])
    assert reversal.params == ["i0"]
    assert reversal.comps == ["comp00"]


def test_set_string_representations():
    BaseConfig.init()
    sample = test_utils.reversal_sample()
    reversal = Reversal(["i0"], ["comp00"])
    schedule = Schedule(sample)
    schedule.add_optimization(reversal)
    assert reversal.tiramisu_optim_str == "comp00.loop_reversal(0);\n\t"


def test_get_candidates():
    BaseConfig.init()
    sample = test_utils.reversal_sample()
    candidates = Reversal.get_candidates(sample.tree)
    assert candidates == {"i0": ["i0", "i1"]}

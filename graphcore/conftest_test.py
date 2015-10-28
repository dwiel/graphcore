import mock
import pytest

from .call_graph import CallGraph
from .conftest import call_graph_repr_compare


def test_call_graph_repr_compare():
    assert call_graph_repr_compare(CallGraph(), CallGraph()) != None


def test_pytest_assertrepr_compare():
    call_graph1 = CallGraph()
    call_graph2 = CallGraph()

    call_graph2.add_node(['a'], [], None, None)

    with mock.patch('graphcore.conftest.call_graph_repr_compare') as fn:
        with pytest.raises(Exception):
            assert call_graph1 == call_graph2 

        # not sure why its getting called more than once ...
        assert len(fn.mock_calls) != 0


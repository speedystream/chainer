import heapq

from chainer import function
from chainer import variable


class DotNode(object):
    """Node of computational graph, with utilities for dot language.

    This class represents a node of computational graph,
    with some utilities for dot language.
    """

    def __init__(self, node):
        """Initialize DotNode.

        Args:
            node: :class: `Variable` object or :class: `Function` object.
        """

        assert isinstance(node, variable.Variable) or\
            isinstance(node, function.Function)
        self.node = node
        self.id_ = id(node)
        self.attribute = {
            "label": self.node.label,
            "shape": self._shape()
        }

    def _shape(self):
        """Return shape type of node."""

        if isinstance(self.node, variable.Variable):
            return "oval"
        elif isinstance(self.node, function.Split):
            return "hexagon"
        else:
            return "box"

    @property
    def label(self):
        """Return a label that represents properties of the node.

        Returns:
            string: A label that represents the id and attributes of this node.
        """

        attributes = ["%s=\"%s\"" % (k, v) for (k, v)
                      in self.attribute.items()]
        return "%s [%s];" % (self.id_, ",".join(attributes))


class ComputationalGraph(object):
    """Class that represents computational graph.

    .. note::

      We assume that the computational graph is directed and acyclic.
    """

    def __init__(self, edges):
        """Initializes computational graph.

        Args:
            edges (list): List of edges. Each edge consists of pair of nodes.
            Nodes are either :class:`Variable` object or
            :class:`Function` object.
        """
        self.edges = edges

    def _to_dot(self):
        """Converts graph in dot format.

        `label` property of is used as short description of each node.
        Returns:
            str: The graph in dot format.
        """

        ret = "digraph graphname{"
        for edge in self.edges:
            head, tail = edge
            assert (isinstance(head, variable.Variable)
                    and isinstance(tail, function.Function)) or \
                   (isinstance(head, function.Function)
                    and isinstance(tail, variable.Variable))
            head_node = DotNode(head)
            tail_node = DotNode(tail)
            ret += head_node.label
            ret += tail_node.label
            ret += "%s -> %s;" % (head_node.id_, tail_node.id_)
        ret += "}"
        return ret

    def dump(self, format='dot'):
        """Dumps graph as a text.

        Args
            format(str): The graph language name of the output.
            Currently, it must be 'dot'

        Returns
            str: The graph in specified format.
        """
        if format == 'dot':
            return self._to_dot()
        else:
            NotImplementedError('Currently, only dot format is supported.')

    def __len__(self):
        return len(self.edges)

    def __contains__(self, e):
        return e in self.edges


def build_computational_graph(outputs, remove_split=True):
    """Build a graph of function or variabls backward-reachable from outputs.

    Args:
        outputs(list): nodes from which the graph is constructed.
        Each element of outputs must be either :class:`Variable`
        object or :class:`Function` object.
        remove_split(bool): If it is `True`, this function hides
        :class:`Split` functions and related variables from the graph.

    Returns:
        :class:`ComputationalGraph`: A graph consisting of nodes and edges that
        are reachable from `outputs`.

        For example, suppose that computational graph is as follows
        (diagram is same as the one in the document of :class:`Function`):

                               |--> x'  ---> f'  ---> y
           x ---> (splitter) --+
                               |--> x'' ---> f'' ---> z

        Let `outputs = [y, z]`.
        If `remove_split` is `False`, this method generates the graph
        itself. If `remove_split` is `True`,
        splitter and x' is removed from the graph and x is directly
        connected to f'. Resulting graph will be

                     |---> y
           x ---> f -+
                     |---> z

        Next, let `outputs = [y]`. Note that `z`, `f''`, and `x''`
        is not backward-reachable from `y`. If `remove_split` is `False`,
        we remove these unreachable nodes to get

           x ---> (splitter) ---> x'  ---> f'  ---> y

        If `remove_split` is `True`, we further remove splitter and `x'` to get

           x ---> f  ---> y

        See `tests/test_computational_graph.py` for details.

    """
    cands = []
    seen_edges = set()

    def heap_with_push_counter():
        push_count = [0]

        def add(cand):
            heapq.heappush(cands, (-cand.rank, push_count[0], cand))
            push_count[0] += 1
        return add

    add_cand = heap_with_push_counter()

    for o in outputs:
        add_cand(o)

    while cands:
        _, _, cand = heapq.heappop(cands)
        if isinstance(cand, variable.Variable):
            creator = cand.creator
            if remove_split and isinstance(creator, function.Split):
                # assume that function.Split has only one input
                next_cand = creator.inputs[0]
                add_cand(next_cand)
                continue
            if creator is not None and (creator, cand) not in seen_edges:
                add_cand(creator)
                seen_edges.add((creator, cand))
        elif isinstance(cand, function.Function):
            if remove_split and isinstance(cand, function.Split):
                next_cand = creator.inputs[0]
                add_cand(next_cand)
                continue
            for input_ in cand.inputs:
                if input_ != cand and (input_, cand) not in seen_edges:
                    creator = input_.creator
                    if remove_split and \
                       creator is not None and \
                       isinstance(creator, function.Split):
                        input_ = creator.inputs[0]
                    add_cand(input_)
                    seen_edges.add((input_, cand))
    return ComputationalGraph(seen_edges)

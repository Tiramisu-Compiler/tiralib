from typing import Dict, List, Tuple
import uuid
from athena.tiramisu.tiramisu_iterator_node import IteratorNode
import itertools


class TiramisuTree:
    """This class represents the tree structure of a Tiramisu program.
    It is composed of a list of IteratorNode objects, each of which represents an iterator
    in the Tiramisu program. Each IteratorNode object contains information about its
    parent iterator, child iterators, lower and upper bounds, and the computations that
    it is associated with.

    Attributes:
    ----------
    `roots`: `List[str]`
        List of names of the root iterators in the Tiramisu program.
    `iterators`: `Dict[str, IteratorNode]`
        Dictionary of IteratorNode objects, indexed by the name of the iterator.
    `computations`: `List[str]`
        List of names of the computations in the Tiramisu program.

    Methods:
    -------
    `from_annotations(cls, annotations: Dict) -> "TiramisuTree":`
        Creates a TiramisuTree object from the annotations of a Tiramisu program.
    `get_candidate_sections(self) -> List[List[str]]:`
        Returns a list of candidate sections in the Tiramisu program.

    """

    def __init__(self) -> None:
        self.roots: List[str] = []
        self.iterators: Dict[str, IteratorNode] = {}
        self.computations: List[str] = []
        self.computations_absolute_order: Dict[str, int] = {}

    def add_root(self, root: str) -> None:
        self.roots.append(root)

    def add_computation(self, comp: str) -> None:
        self.computations.append(comp)

    @classmethod
    def from_annotations(cls, annotations: Dict) -> "TiramisuTree":
        """
        Creates a TiramisuTree object from the annotations of a Tiramisu program.

        Parameters:
        ----------
        `annotations`: `Dict`
            Annotations of a Tiramisu program.

        Returns:
        -------
        `tiramisu_space`: `TiramisuTree`
        """
        tiramisu_space = cls()

        iterators = annotations["iterators"]

        tiramisu_space.computations_absolute_order = {
            comp: annotations["computations"][comp]["absolute_order"]
            for comp in annotations["computations"]
        }

        # order keys of computations_absolute_order by their values
        tiramisu_space.computations = [
            comp
            for comp, _ in sorted(
                tiramisu_space.computations_absolute_order.items(),
                key=lambda item: item[1],
            )
        ]

        for iterator in iterators:
            parent_iterator = iterators[iterator]["parent_iterator"]
            iterator_level = None
            if parent_iterator is None:
                tiramisu_space.add_root(iterator)
                iterator_level = 0
            else:
                iterator_level = tiramisu_space.iterators[parent_iterator].level + 1

            # get the computations that are associated with this iterator ordered by their absolute order
            ordered_node_comps = [
                comp
                for comp in tiramisu_space.computations
                if comp in iterators[iterator]["computations_list"]
            ]

            tiramisu_space.iterators[iterator] = IteratorNode(
                name=iterator,
                lower_bound=int(iterators[iterator]["lower_bound"]),
                upper_bound=int(iterators[iterator]["upper_bound"]),
                child_iterators=iterators[iterator]["child_iterators"],
                computations_list=ordered_node_comps,
                parent_iterator=iterators[iterator]["parent_iterator"],
                level=iterator_level,
            )

        # order the roots by their first comp's absolute order
        root_with_order = []
        for root in tiramisu_space.roots:
            first_comp = tiramisu_space.get_iterator_subtree_computations(root)[0]
            first_comp_order = tiramisu_space.computations_absolute_order[first_comp]
            root_with_order.append((root, first_comp_order))

        tiramisu_space.roots = [
            root for root, _ in sorted(root_with_order, key=lambda item: item[1])
        ]

        return tiramisu_space

    def _get_subtree_representation(self, node_name: str) -> str:
        representation = ""
        for node in self.iterators[node_name].child_iterators:
            representation += (
                "   " * self.iterators[node].level
                + "-> "
                + repr(self.iterators[node])
                + "\n"
            )
            # representation += "   " * self.iterators[node].level + "-> " + node + "\n"
            for comp in self.iterators[node].computations_list:
                representation += (
                    "   " * (self.iterators[node].level + 1) + "- " + comp + "\n"
                )
            representation += self._get_subtree_representation(node)
        return representation

    def get_candidate_sections(self) -> Dict[str, List[List[str]]]:
        """
        Returns a dictionary with lists of candidate sections for each root iterator.

        Returns:
        -------

        `candidate_sections`: `Dict[str, List[List[str]]]`
            Dictionary with lists of candidate sections for each root iterator.
        """

        candidate_sections = {}
        for root in self.roots:
            nodes_to_visit = [root]
            list_candidate_sections = []
            for node in nodes_to_visit:
                candidate_section, new_nodes_to_visit = self._get_section_of_node(node)
                list_candidate_sections.append(candidate_section)
                nodes_to_visit.extend(new_nodes_to_visit)
            candidate_sections[root] = list_candidate_sections
        return candidate_sections

    def _get_section_of_node(self, node_name: str) -> Tuple[List[str], List[str]]:
        candidate_section = [node_name]
        current_node = self.iterators[node_name]

        while (
            len(current_node.child_iterators) == 1
            and len(current_node.computations_list) == 0
        ):
            next_node_name = current_node.child_iterators[0]
            candidate_section.append(next_node_name)
            current_node = self.iterators[next_node_name]

        if current_node.child_iterators:
            return candidate_section, current_node.child_iterators
        return candidate_section, []

    def get_iterator_subtree_computations(self, candidate_node_name: str) -> List[str]:
        """Get the list of computations impacted by this node

        Parameters:
        ----------
        `candidate_node`: `IteratorNode`
            The candidate node for parallelization.

        `program_tree`: `TiramisuTree`
            The Tiramisu tree of the program.

        Returns:
        -------
        `list`
            List of computations impacted by the node
        """

        computations: List[str] = []
        candidate_node = self.iterators[candidate_node_name]

        computations += candidate_node.computations_list

        for child in candidate_node.child_iterators:
            computations += self.get_iterator_subtree_computations(child)

        return computations

    def get_iterator_levels(self, iterators_list: List[str]) -> List[int]:
        """
        This function returns the levels of the iterators in the computation
        """
        return [self.iterators[iterator].level for iterator in iterators_list]

    def get_iterator_node(self, iterator_name: str) -> IteratorNode:
        """
        This function returns the iterator node corresponding to the iterator name
        """
        return self.iterators[iterator_name]

    def get_root_of_node(self, iterator_name: str) -> str:
        # Get the root node of the iterator
        current_node_name = iterator_name

        while self.iterators[current_node_name].parent_iterator:  # type: ignore
            current_node_name = self.iterators[current_node_name].parent_iterator  # type: ignore

        if current_node_name is None:
            raise ValueError("The iterator has no root node")

        return current_node_name

    def get_iterator_of_computation(self, computation_name: str):
        """
        This function returns the iterator of the computation
        """
        for iterator in self.iterators:
            if computation_name in self.iterators[iterator].computations_list:
                return self.iterators[iterator]

        raise ValueError("The computation is not in the tree")

    def clone_subtree(
        self,
        node: str,
        suffix: str = f"_clone_{uuid.uuid4()}",
        tiramisu_tree: "TiramisuTree" = None,
    ):
        """
        This function clones the subtree rooted at the node
        """
        if node not in self.iterators:
            raise ValueError("The node is not in the tree")

        is_root = False

        new_node = self.iterators[node].clone(suffix)
        if tiramisu_tree is None:
            is_root = True
            tiramisu_tree = TiramisuTree()
            tiramisu_tree.add_root(new_node.name)

        tiramisu_tree.iterators[new_node.name] = new_node
        tiramisu_tree.computations += new_node.computations_list

        for child in self.iterators[node].child_iterators:
            self.clone_subtree(child, suffix, tiramisu_tree=tiramisu_tree)

        if is_root:
            tiramisu_tree.computations.sort(
                key=lambda x: self.computations_absolute_order[x.replace(suffix, "")]
            )
            tiramisu_tree.computations_absolute_order = {
                comp: i + 1 for i, comp in enumerate(tiramisu_tree.computations)
            }
            tiramisu_tree.update_subtree_levels(tiramisu_tree.roots[0], 0)
            new_node.parent_iterator = None

        return tiramisu_tree

    def insert_subtree(
        self, subtree: "TiramisuTree", parent_node: str, is_root_parent: bool = False
    ):
        """
        This function inserts the subtree rooted at the subtree_root
        into the parent_node
        """

        if parent_node not in self.iterators:
            raise ValueError("The node is not in the tree")

        subtree_root = subtree.roots[0]

        for node in subtree.iterators:
            self.iterators[node] = subtree.iterators[node]

        # get order of last computation of parent node
        parent_node_list = self.get_iterator_subtree_computations(parent_node)
        parent_node_list.sort(key=lambda x: self.computations_absolute_order[x])
        last_comp_order = self.computations_absolute_order[parent_node_list[-1]]

        # update computations absosulte orde
        computations_to_update = [
            comp
            for comp in self.computations_absolute_order
            if self.computations_absolute_order[comp] > last_comp_order
        ]

        nbr_comps = len(subtree.computations)

        for comp in computations_to_update:
            self.computations_absolute_order[comp] += nbr_comps

        for i, comp in enumerate(subtree.computations):
            self.computations_absolute_order[comp] = last_comp_order + i + 1

        if is_root_parent:
            self.roots.append(subtree_root)
            subtree.iterators[subtree_root].parent_iterator = None
        else:
            self.iterators[parent_node].child_iterators.append(subtree_root)
            subtree.iterators[subtree_root].parent_iterator = parent_node

        self.computations += subtree.computations
        self.computations.sort(key=lambda x: self.computations_absolute_order[x])

        # update levels
        if is_root_parent:
            self.update_subtree_levels(subtree_root, 0)
            # sort roots
            self.roots.sort(
                key=lambda x: self.computations_absolute_order[
                    self.get_iterator_subtree_computations(x)[0]
                ]
            )
        else:
            self.update_subtree_levels(parent_node, self.iterators[parent_node].level)

    def update_subtree_levels(self, node: str, level: int):
        """
        This function updates the levels of the subtree rooted at the node
        """
        if node not in self.iterators:
            raise ValueError("The node is not in the tree")

        self.iterators[node].level = level

        for child in self.iterators[node].child_iterators:
            self.update_subtree_levels(child, level + 1)

    def get_comp_iterator(self, comp: str, level: int) -> str:
        """
        This function returns the iterator at level `level` of the computation
        """
        current_iterator = None
        for iterator in self.iterators:
            if comp in self.iterators[iterator].computations_list:
                current_iterator = self.iterators[iterator]
                break

        if current_iterator is None:
            raise ValueError("The computation is not in the tree")

        while current_iterator.level > level:
            assert current_iterator.parent_iterator is not None
            current_iterator = self.iterators[current_iterator.parent_iterator]

        return current_iterator.name

    def __str__(self) -> str:
        # return f"Roots: {self.roots}\nComputations: {self.computations}\nIterators: {self.iterators}"
        representation = ""

        for root in self.roots:
            representation += "-> " + repr(self.iterators[root]) + "\n"
            for comp in self.iterators[root].computations_list:
                representation += (
                    "   " * (self.iterators[root].level + 1) + "- " + comp + "\n"
                )
            # representation += "-> " + root + "\n"
            representation += self._get_subtree_representation(root)

        return representation

    def __repr__(self) -> str:
        return self.__str__()

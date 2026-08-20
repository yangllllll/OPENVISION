"""流程图执行引擎 - 按拓扑顺序执行节点"""

from collections import deque
from typing import Any, Dict, List, Optional, Set

from app.flowchart.node import NodeItem
from app.flowchart.connection import ConnectionItem
from app.flowchart.port import PortItem


class ExecutionEngine:
    """执行引擎"""

    def __init__(self):
        self._nodes: Dict[str, NodeItem] = {}
        self._connections: List[ConnectionItem] = []
        self._running = False
        self._results: Dict[str, Any] = {}

    def setup(self, nodes: Dict[str, NodeItem], connections: List[ConnectionItem]):
        self._nodes = nodes
        self._connections = connections
        self._results.clear()

    def _build_graph(self) -> Dict[str, List[str]]:
        """构建邻接表（从源端口节点到目标端口节点）"""
        adj: Dict[str, List[str]] = {}

        for node_id in self._nodes:
            adj[node_id] = []

        for conn in self._connections:
            if conn.source_port and conn.target_port:
                src_id = conn.source_port.parent_node.node_id
                tgt_id = conn.target_port.parent_node.node_id
                if src_id in adj:
                    adj[src_id].append(tgt_id)

        return adj

    def topological_sort(self) -> Optional[List[str]]:
        """拓扑排序，返回执行顺序"""
        adj = self._build_graph()
        in_degree: Dict[str, int] = {nid: 0 for nid in self._nodes}

        for src, targets in adj.items():
            for tgt in targets:
                if tgt in in_degree:
                    in_degree[tgt] += 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order = []

        while queue:
            node_id = queue.popleft()
            order.append(node_id)
            for neighbor in adj.get(node_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self._nodes):
            return None  # 有环

        return order

    def _transfer_data(self):
        """通过连接传输数据"""
        for conn in self._connections:
            if conn.source_port and conn.target_port:
                src_node = conn.source_port.parent_node
                tgt_node = conn.target_port.parent_node
                src_port_name = conn.source_port.port_name
                tgt_port_name = conn.target_port.port_name

                src_outputs = src_node.plugin.get_outputs()
                if src_port_name in src_outputs:
                    tgt_node.plugin.set_input(tgt_port_name, src_outputs[src_port_name])

    def execute(self) -> Dict[str, Any]:
        """执行整个流程图"""
        self._running = True
        self._results.clear()

        order = self.topological_sort()
        if order is None:
            self._results["_error"] = "流程图存在循环依赖，无法执行"
            self._running = False
            return self._results

        for node_id in order:
            node = self._nodes[node_id]
            node.plugin.reset()

        errors = []
        for node_id in order:
            node = self._nodes[node_id]
            self._transfer_data()
            try:
                success = node.plugin.execute()
                if success:
                    self._results[node_id] = node.plugin.get_outputs()
                else:
                    err = node.plugin.get_last_error() or "执行失败"
                    self._results[node_id] = err
                    errors.append(f"{node.plugin_name}: {err}")
                    # 失败节点清空输出，防止向下游传递无效数据
                    node.plugin.reset()
            except Exception as e:
                self._results[node_id] = str(e)
                errors.append(f"{node.plugin_name}: {e}")
                node.plugin.reset()

        if errors:
            self._results["_error"] = "; ".join(errors)

        self._running = False
        return self._results

    def get_node_results(self, node_id: str) -> Dict[str, Any]:
        return self._results.get(node_id, {})
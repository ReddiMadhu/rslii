"""Core AST parser — walks Python AST to extract ETL nodes and edges."""

import ast
import os
import textwrap
from typing import Optional

from .operations import (
    EXTERNAL_READ_METHODS,
    FORMAT_MAP,
    classify_method,
    get_category_info,
    READ_OPS,
    WRITE_OPS,
    SUBSCRIPT_FILTER_ATTRS,
    STR_ACCESSOR,
)


class ETLNode:
    """Represents a single ETL operation in the lineage."""

    def __init__(self, node_id: str, category: str, op_type: str, method: str,
                 label: str, code: str, line_number: int, variable_out: str = "",
                 is_loop: bool = False, pipeline_id: int = 0):
        self.id = node_id
        self.category = category
        self.type = op_type
        self.method = method
        self.label = label
        self.code = code
        self.line_number = line_number
        self.variable_out = variable_out
        self.is_loop = is_loop
        self.pipeline_id = pipeline_id
        self.schema_refs: list[str] = []
        self.description = ""
        self.description_source = "template"
        # Resolved path / connection string for source nodes (v2 file mapping)
        self.source_connection: str = ""
        # agg / aggregate: output column name -> input column(s) (named aggregation)
        self.column_sources: dict[str, list[str]] = {}

    def to_dict(self) -> dict:
        info = get_category_info(self.category)
        d = {
            "id": self.id,
            "type": self.type,
            "category": self.category,
            "method": self.method,
            "label": self.label,
            "description": self.description,
            "description_source": self.description_source,
            "code": self.code,
            "line_number": self.line_number,
            "schema_refs": self.schema_refs,
            "is_loop": self.is_loop,
            "pipeline_id": self.pipeline_id,
            "variable_out": self.variable_out,
            "color": info["color"],
            "icon": info["icon"],
        }
        if self.column_sources:
            d["column_sources"] = self.column_sources
        return d


class ETLEdge:
    """Represents a data flow connection between two nodes."""

    def __init__(self, source: str, target: str, variable: str = ""):
        self.source = source
        self.target = target
        self.variable = variable

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "variable": self.variable,
        }


class ASTParser:
    """Parses Python AST to extract ETL lineage nodes and edges."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.tree = ast.parse(source_code)
        self.nodes: list[ETLNode] = []
        self.edges: list[ETLEdge] = []
        self.warnings: list[dict] = []
        self._node_counter = 0
        # Variable tracking: var_name -> last node_id that wrote to it
        self._var_map: dict[str, str] = {}
        # Function definitions for call resolution
        self._func_defs: dict[str, ast.FunctionDef] = {}
        # v2 execution: ordered instrumentation points (same tree as self.tree)
        self.injection_steps: list[dict] = []

    def parse(self) -> dict:
        """Main entry point — parse the code and return the full result."""
        self.injection_steps = []
        # Step 1: Collect function definitions
        self._collect_function_defs()

        # Step 2: Find entry point
        main_body = self._find_main_body()

        # Step 3: Walk the statements
        self._walk_statements(main_body, in_loop=False)

        # Step 4: Detect disconnected pipelines
        self._assign_pipeline_ids()

        # Step 5: Generate summary
        summary = self._build_summary()

        return {
            "summary": summary,
            "llm_used": False,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "warnings": self.warnings,
        }

    def extract_sources(self) -> list[dict]:
        """
        Structured file-mapping slots for v2 (call after parse()).
        One entry per AST source node, in discovery order.
        """
        sources: list[dict] = []
        for node in self.nodes:
            if node.category != "source":
                continue
            fmt = FORMAT_MAP.get(node.method, "unknown")
            path = node.source_connection or None
            if path == "unknown":
                path = None
            filename = self._source_filename_from_path(path, node.method)
            requires_upload = True
            skip_reason: Optional[str] = None
            if node.method == "DataFrame":
                requires_upload = False
            elif node.method in EXTERNAL_READ_METHODS:
                requires_upload = False
                skip_reason = "External source"
            sources.append({
                "id": f"source_{len(sources) + 1}",
                "method": node.method,
                "format": fmt,
                "path": path,
                "filename": filename,
                "line": node.line_number,
                "node_id": node.id,
                "requires_upload": requires_upload,
                "skip_reason": skip_reason,
            })
        return sources

    def build_parse_skeleton(self) -> dict:
        """Minimal DAG for /api/parse (after parse())."""
        sk_nodes = []
        for n in self.nodes:
            info = get_category_info(n.category)
            sk_nodes.append({
                "id": n.id,
                "label": n.label,
                "category": n.category,
                "color": info["color"],
                "icon": info["icon"],
                "line_number": n.line_number,
            })
        return {"nodes": sk_nodes, "edges": [e.to_dict() for e in self.edges]}

    @staticmethod
    def _source_filename_from_path(path: Optional[str], method: str) -> Optional[str]:
        if not path:
            return None
        if path.startswith("env(") or path.startswith("config("):
            return path
        if method in EXTERNAL_READ_METHODS:
            return None
        base = os.path.basename(path.strip().strip('"').strip("'"))
        return base or None

    # ─── Entry Point Resolution ───

    def _collect_function_defs(self):
        """Collect all function definitions in the file."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                self._func_defs[node.name] = node

    def _find_main_body(self) -> list[ast.stmt]:
        """Find the main execution body — __main__ guard or top-level."""
        for node in self.tree.body:
            if isinstance(node, ast.If):
                # Check for: if __name__ == "__main__":
                test = node.test
                if (isinstance(test, ast.Compare)
                        and isinstance(test.left, ast.Name)
                        and test.left.id == "__name__"
                        and len(test.comparators) == 1
                        and isinstance(test.comparators[0], ast.Constant)
                        and test.comparators[0].value == "__main__"):
                    return node.body

        # Fallback: all top-level statements except function/class defs
        return [stmt for stmt in self.tree.body
                if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef,
                                         ast.ClassDef, ast.Import, ast.ImportFrom))]

    # ─── Statement Walking ───

    def _walk_statements(self, stmts: list[ast.stmt], in_loop: bool = False):
        """Walk a list of statements, extracting ETL operations."""
        for stmt in stmts:
            if isinstance(stmt, ast.Assign):
                self._handle_assign(stmt, in_loop)
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                self._handle_expr_call(stmt, in_loop)
            elif isinstance(stmt, (ast.For, ast.While)):
                self._walk_statements(stmt.body, in_loop=True)
            elif isinstance(stmt, ast.If):
                self._walk_statements(stmt.body, in_loop)
                if stmt.orelse:
                    self._walk_statements(stmt.orelse, in_loop)
            elif isinstance(stmt, ast.With):
                self._walk_statements(stmt.body, in_loop)

    def _handle_assign(self, stmt: ast.Assign, in_loop: bool):
        """Handle assignment statements like `df = pd.read_csv(...)`."""
        target_var = self._get_assign_target(stmt)
        value = stmt.value

        # Check for column assignment: df['new'] = ...
        if (len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Subscript)
                and isinstance(stmt.targets[0].slice, ast.Constant)
                and isinstance(stmt.targets[0].slice.value, str)):
            col_name = stmt.targets[0].slice.value
            var_name = self._get_var_name(stmt.targets[0].value)
            code_str = self._get_source(stmt)
            node = self._create_node(
                category="column_op", op_type="column_op", method="column_assign",
                label=f"Create Column: {col_name}",
                code=code_str, line=stmt.lineno, variable_out=var_name or "",
                in_loop=in_loop,
            )
            node.schema_refs = [col_name]
            if var_name and var_name in self._var_map:
                self._add_edge(self._var_map[var_name], node.id, var_name)
            if var_name:
                self._var_map[var_name] = node.id
            self.injection_steps.append({
                "node_id": node.id,
                "method": "column_assign",
                "category": "column_op",
                "parent_stmt": stmt,
                "call_node": None,
                "snapshot_var": var_name or "",
            })
            return

        # Process the value expression — may produce multiple nodes from chains
        self._process_expression(value, target_var, in_loop, parent_stmt=stmt)

    def _handle_expr_call(self, stmt: ast.Expr, in_loop: bool):
        """Handle bare expression calls like `df.to_csv(...)`."""
        self._process_expression(stmt.value, None, in_loop, parent_stmt=stmt)

    # ─── Expression Processing ───

    def _process_expression(
        self,
        expr,
        target_var: Optional[str],
        in_loop: bool,
        parent_stmt: Optional[ast.stmt] = None,
    ):
        """Process an expression, handling chains, calls, and subscripts."""
        # Unpack chained method calls into a flat list
        chain = self._unpack_chain(expr)

        if not chain:
            # Single non-chain expression — try to classify
            self._process_single_expr(expr, target_var, in_loop, parent_stmt=parent_stmt)
            return

        prev_node_id = None
        prev_var = None

        for i, (method_name, call_node, full_expr) in enumerate(chain):
            category, op_type = classify_method(method_name)
            is_last = (i == len(chain) - 1)

            # Extract details for label
            label = self._build_label(method_name, category, call_node)
            code_str = self._get_source_from_node(full_expr)

            var_out = target_var if is_last else f"_chain_{self._node_counter}"
            if target_var is None and is_last and category == "target":
                if isinstance(call_node.func, ast.Attribute):
                    receiver = self._get_var_name(call_node.func.value)
                    if receiver:
                        var_out = receiver
            node = self._create_node(
                category=category, op_type=op_type, method=method_name,
                label=label, code=code_str, line=full_expr.lineno,
                variable_out=var_out, in_loop=in_loop,
            )

            # Extract schema refs
            node.schema_refs = self._extract_schema_refs(call_node)
            if method_name in ("agg", "aggregate") and isinstance(call_node, ast.Call):
                node.column_sources = self._extract_agg_column_sources(call_node)

            if category == "source":
                node.source_connection = self._extract_connection(call_node)

            if parent_stmt is not None:
                self.injection_steps.append({
                    "node_id": node.id,
                    "method": method_name,
                    "category": category,
                    "parent_stmt": parent_stmt,
                    "call_node": call_node,
                    "snapshot_var": var_out or "",
                })

            # For merge/join operations, connect extra inputs (the "right" DataFrame)
            if category == "join":
                self._connect_merge_inputs(call_node, node)

            # Connect to previous node in chain
            if prev_node_id:
                self._add_edge(prev_node_id, node.id, prev_var or "")
            elif i == 0:
                # First in chain — connect to source variable
                source_var = self._get_chain_source_var(full_expr)
                if source_var and source_var in self._var_map:
                    self._add_edge(self._var_map[source_var], node.id, source_var)

            prev_node_id = node.id
            prev_var = var_out

        # Map the final variable
        if target_var and prev_node_id:
            self._var_map[target_var] = prev_node_id

    def _process_single_expr(
        self,
        expr,
        target_var: Optional[str],
        in_loop: bool,
        parent_stmt: Optional[ast.stmt] = None,
    ):
        """Process a single (non-chain) expression."""
        # Boolean indexing: df[df['col'] > value]
        if isinstance(expr, ast.Subscript):
            var_name = self._get_var_name(expr.value)
            code_str = self._get_source_from_node(expr)
            condition = self._get_source_from_node(expr.slice) if expr.slice else "condition"
            node = self._create_node(
                category="filter", op_type="filter", method="boolean_index",
                label=f"Filter: {self._truncate(condition, 40)}",
                code=code_str, line=expr.lineno,
                variable_out=target_var or "", in_loop=in_loop,
            )
            if var_name and var_name in self._var_map:
                self._add_edge(self._var_map[var_name], node.id, var_name)
            if target_var:
                self._var_map[target_var] = node.id
            if parent_stmt is not None:
                self.injection_steps.append({
                    "node_id": node.id,
                    "method": "boolean_index",
                    "category": "filter",
                    "parent_stmt": parent_stmt,
                    "call_node": None,
                    "snapshot_var": target_var or "",
                })
            return

        # Function call (user-defined or unknown)
        if isinstance(expr, ast.Call):
            func_name = self._get_func_name(expr)
            if func_name and func_name in self._func_defs:
                self._resolve_function_call(func_name, expr, target_var, in_loop)
                return

            # pd.concat, pd.merge etc.
            if func_name:
                category, op_type = classify_method(func_name)
                if category != "unknown":
                    label = self._build_label(func_name, category, expr)
                    code_str = self._get_source_from_node(expr)
                    node = self._create_node(
                        category=category, op_type=op_type, method=func_name,
                        label=label, code=code_str, line=expr.lineno,
                        variable_out=target_var or "", in_loop=in_loop,
                    )
                    if category == "source":
                        node.source_connection = self._extract_connection(expr)
                    if parent_stmt is not None:
                        self.injection_steps.append({
                            "node_id": node.id,
                            "method": func_name,
                            "category": category,
                            "parent_stmt": parent_stmt,
                            "call_node": expr,
                            "snapshot_var": target_var or "",
                        })
                    # For concat/merge, try to connect input variables
                    self._connect_merge_inputs(expr, node)
                    if target_var:
                        self._var_map[target_var] = node.id
                    return

        # If we can't classify it, skip (don't create unknown nodes for imports etc.)

    # ─── Chain Unpacking ───

    def _unpack_chain(self, expr) -> list[tuple[str, ast.Call, ast.AST]]:
        """
        Unpack a chained method call like df.a().b().c() into:
        [(method_a, call_a, expr_a), (method_b, call_b, expr_b), ...]
        Returns list in execution order (innermost first).
        """
        chain = []
        current = expr

        while isinstance(current, ast.Call):
            func = current.func
            if isinstance(func, ast.Attribute):
                method_name = func.attr
                # Skip user-defined function calls — let them be resolved separately
                if method_name in self._func_defs:
                    break
                chain.append((method_name, current, current))
                current = func.value  # go deeper into the chain
            else:
                # Top-level function call (pd.read_csv, pd.concat, etc.)
                func_name = self._get_func_name(current)
                if func_name:
                    # Skip user-defined functions — they need full resolution
                    if func_name in self._func_defs:
                        break
                    category, _ = classify_method(func_name)
                    if category != "unknown":
                        chain.append((func_name, current, current))
                break

        # chain is in reverse order (outermost first), reverse it
        chain.reverse()
        return chain if len(chain) > 0 else []

    # ─── Function Call Resolution ───

    def _resolve_function_call(self, func_name: str, call_node: ast.Call,
                                target_var: Optional[str], in_loop: bool):
        """Resolve a user-defined function call and inline its ETL operations."""
        func_def = self._func_defs[func_name]

        # Map arguments to parameters
        old_var_map = dict(self._var_map)
        for i, arg in enumerate(call_node.args):
            if i < len(func_def.args.args):
                param_name = func_def.args.args[i].arg
                arg_var = self._get_var_name(arg)
                if arg_var and arg_var in self._var_map:
                    self._var_map[param_name] = self._var_map[arg_var]

        # Walk the function body
        self._walk_statements(func_def.body, in_loop)

        # Map return value to target variable
        if target_var:
            # Find the last return statement's variable
            for stmt in reversed(func_def.body):
                if isinstance(stmt, ast.Return) and stmt.value:
                    ret_var = self._get_var_name(stmt.value)
                    if ret_var and ret_var in self._var_map:
                        self._var_map[target_var] = self._var_map[ret_var]
                    break

    # ─── Connection String Extraction ───

    def _extract_connection(self, call_node: ast.Call) -> str:
        """Extract the source/target path from a read/write call."""
        if not call_node.args:
            # Check keyword args
            for kw in call_node.keywords:
                if kw.arg in ("filepath_or_buffer", "path_or_buf", "path", "name", "con"):
                    return self._resolve_value(kw.value)
            return "unknown"
        return self._resolve_value(call_node.args[0])

    def _resolve_value(self, node) -> str:
        """Resolve an AST value node to a display string."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Subscript):
            # os.environ["KEY"]
            val = self._get_var_name(node.value)
            if val and "environ" in val:
                key = self._get_source_from_node(node.slice)
                return f"env({key.strip(chr(34)).strip(chr(39))})"
        if isinstance(node, ast.Call):
            # config.get("key")
            func_name = self._get_func_name(node) or self._get_attr_name(node)
            if func_name and "get" in func_name and node.args:
                key_val = self._resolve_value(node.args[0])
                return f"config({key_val})"
        return self._get_source_from_node(node) or "unknown"

    # ─── Label Building ───

    def _build_label(self, method: str, category: str, call_node: ast.Call) -> str:
        """Build a human-readable label for a node."""
        if method == "DataFrame":
            return "Create DataFrame (inline)"
        if category == "source":
            conn = self._extract_connection(call_node)
            fmt = method.replace("read_", "").upper()
            return f"Read {fmt}: {self._truncate(conn, 30)}"

        if category == "target":
            conn = self._extract_connection(call_node)
            fmt = method.replace("to_", "").upper()
            return f"Write {fmt}: {self._truncate(conn, 30)}"

        if method == "merge":
            on = self._get_keyword_str(call_node, "on")
            how = self._get_keyword_str(call_node, "how")
            parts = []
            if how:
                parts.append(how.capitalize())
            parts.append("Merge")
            if on:
                parts.append(f"on: {on}")
            return " ".join(parts)

        if method == "join":
            on = self._get_keyword_str(call_node, "on")
            return f"Join{f' on: {on}' if on else ''}"

        if method == "concat":
            return "Concat DataFrames"

        if method == "groupby":
            by = self._get_first_arg_str(call_node)
            return f"GroupBy: {self._truncate(by, 30)}" if by else "GroupBy"

        if method == "query":
            expr = self._get_first_arg_str(call_node)
            return f"Query: {self._truncate(expr, 35)}" if expr else "Query"

        if method == "dropna":
            subset = self._get_keyword_str(call_node, "subset")
            return f"Drop NA{f' in: {subset}' if subset else ''}"

        if method == "fillna":
            val = self._get_first_arg_str(call_node)
            return f"Fill NA{f' with: {val}' if val else ''}"

        if method == "rename":
            return "Rename Columns"

        if method == "drop":
            return "Drop Columns"

        if method in ("sort_values", "sort_index"):
            by = self._get_first_arg_str(call_node)
            return f"Sort: {self._truncate(by, 30)}" if by else "Sort"

        if method == "apply":
            return "Apply Transform"

        if method == "pivot_table":
            return "Pivot Table"

        if method in ("melt", "pivot", "stack", "unstack"):
            return method.capitalize()

        if method == "astype":
            return "Type Cast"

        if method == "reset_index":
            return "Reset Index"

        if method == "set_index":
            col = self._get_first_arg_str(call_node)
            return f"Set Index: {col}" if col else "Set Index"

        if method == "drop_duplicates":
            return "Drop Duplicates"

        if method == "replace":
            return "Replace Values"

        if method in ("value_counts",):
            return "Value Counts"

        # Fallback
        cat_info = get_category_info(category)
        return f"{cat_info['label']}: {method}"

    # ─── Schema Reference Extraction ───

    def _extract_agg_column_sources(self, call_node: ast.Call) -> dict[str, list[str]]:
        """Map aggregation output columns to source column(s) for named / dict .agg().

        Supports ``.agg(out=("src", "mean"))`` and ``.agg({"col": "sum"})``.
        """
        out: dict[str, list[str]] = {}
        if not isinstance(call_node.func, ast.Attribute):
            return out
        if call_node.func.attr not in ("agg", "aggregate"):
            return out

        def tuple_first_cols(tup: ast.Tuple) -> list[str]:
            if not tup.elts:
                return []
            first = tup.elts[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                return [first.value]
            if isinstance(first, ast.List):
                acc: list[str] = []
                for elt in first.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        acc.append(elt.value)
                return acc
            return []

        # Positional dict: .agg({"amount": "sum", "qty": "mean"})
        for arg in call_node.args:
            if isinstance(arg, ast.Dict):
                for k in arg.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        name = k.value
                        out.setdefault(name, [name])

        # Keyword named aggregation: avg=("loss", "mean")
        for kw in call_node.keywords:
            if kw.arg is None:
                continue
            if isinstance(kw.value, ast.Tuple) and kw.value.elts:
                cols = tuple_first_cols(kw.value)
                if cols:
                    out[kw.arg] = cols

        return out

    def _extract_schema_refs(self, call_node: ast.Call) -> list[str]:
        """Extract column names referenced in a call."""
        refs = []
        for node in ast.walk(call_node):
            # df['column'] or df["column"]
            if (isinstance(node, ast.Subscript)
                    and isinstance(node.slice, ast.Constant)
                    and isinstance(node.slice.value, str)):
                refs.append(node.slice.value)
            # keyword like on="col"
            if (isinstance(node, ast.keyword)
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                    and node.arg in ("on", "by", "subset", "columns")):
                refs.append(node.value.value)
            # keyword with list: on=["a", "b"]
            if (isinstance(node, ast.keyword)
                    and isinstance(node.value, ast.List)
                    and node.arg in ("on", "by", "subset", "columns")):
                for elt in node.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        refs.append(elt.value)
        return list(dict.fromkeys(refs))  # dedupe preserving order

    # ─── Merge Input Connection ───

    def _connect_merge_inputs(self, call_node: ast.Call, node: ETLNode):
        """Connect input variables for merge/concat operations."""
        # pd.concat([df1, df2]) — list of DataFrames
        for arg in call_node.args:
            if isinstance(arg, ast.List):
                for elt in arg.elts:
                    var = self._get_var_name(elt)
                    if var and var in self._var_map:
                        self._add_edge(self._var_map[var], node.id, var)
        # df1.merge(df2, ...) — self is already connected via chain
        if call_node.args:
            var = self._get_var_name(call_node.args[0])
            if var and var in self._var_map:
                self._add_edge(self._var_map[var], node.id, var)

    # ─── Pipeline Detection ───

    def _assign_pipeline_ids(self):
        """Find disconnected components and assign pipeline IDs."""
        if not self.nodes:
            return

        # Build adjacency
        node_ids = {n.id for n in self.nodes}
        adj: dict[str, set[str]] = {nid: set() for nid in node_ids}
        for e in self.edges:
            if e.source in adj and e.target in adj:
                adj[e.source].add(e.target)
                adj[e.target].add(e.source)

        visited = set()
        pipeline_id = 0

        for nid in [n.id for n in self.nodes]:
            if nid in visited:
                continue
            # BFS
            queue = [nid]
            component = []
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)
                queue.extend(adj.get(current, set()) - visited)

            for cid in component:
                for n in self.nodes:
                    if n.id == cid:
                        n.pipeline_id = pipeline_id
            pipeline_id += 1

    # ─── Summary Builder ───

    def _build_summary(self) -> dict:
        sources = []
        targets = []
        metrics = {
            "filters": 0, "joins": 0, "aggregations": 0, "cleaning": 0,
            "reshapes": 0, "column_ops": 0, "sort_index": 0, "apply_map": 0,
        }

        for n in self.nodes:
            if n.category == "source":
                fmt = FORMAT_MAP.get(n.method, n.method.replace("read_", "") or "unknown")
                sources.append({"name": n.label, "format": fmt, "line": n.line_number})
            elif n.category == "target":
                targets.append({"name": n.label, "format": n.method.replace("to_", ""), "line": n.line_number})
            elif n.category == "filter":
                metrics["filters"] += 1
            elif n.category == "join":
                metrics["joins"] += 1
            elif n.category == "aggregation":
                metrics["aggregations"] += 1
            elif n.category == "clean":
                metrics["cleaning"] += 1
            elif n.category == "reshape":
                metrics["reshapes"] += 1
            elif n.category == "column_op":
                metrics["column_ops"] += 1
            elif n.category == "sort":
                metrics["sort_index"] += 1
            elif n.category == "apply":
                metrics["apply_map"] += 1

        pipeline_ids = set(n.pipeline_id for n in self.nodes) if self.nodes else set()

        return {
            "sources": sources,
            "targets": targets,
            "metrics": metrics,
            "total_nodes": len(self.nodes),
            "total_lines": len(self.source_lines),
            "pipeline_count": len(pipeline_ids),
            "warning_count": len(self.warnings),
        }

    # ─── Helper Methods ───

    def _create_node(self, category: str, op_type: str, method: str, label: str,
                     code: str, line: int, variable_out: str, in_loop: bool) -> ETLNode:
        self._node_counter += 1
        node = ETLNode(
            node_id=f"node_{self._node_counter}",
            category=category, op_type=op_type, method=method,
            label=label, code=code, line_number=line,
            variable_out=variable_out, is_loop=in_loop,
        )
        self.nodes.append(node)
        return node

    def _add_edge(self, source_id: str, target_id: str, variable: str):
        # Avoid duplicate edges
        for e in self.edges:
            if e.source == source_id and e.target == target_id:
                return
        self.edges.append(ETLEdge(source_id, target_id, variable))

    def _get_assign_target(self, stmt: ast.Assign) -> Optional[str]:
        if stmt.targets and isinstance(stmt.targets[0], ast.Name):
            return stmt.targets[0].id
        return None

    def _get_var_name(self, node) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return None

    def _get_func_name(self, call_node: ast.Call) -> Optional[str]:
        func = call_node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return None

    def _get_attr_name(self, call_node: ast.Call) -> Optional[str]:
        func = call_node.func
        if isinstance(func, ast.Attribute):
            val = self._get_var_name(func.value)
            return f"{val}.{func.attr}" if val else func.attr
        return None

    def _get_chain_source_var(self, expr) -> Optional[str]:
        """Get the root variable of a chain: df.a().b() -> 'df'."""
        current = expr
        while isinstance(current, ast.Call):
            current = current.func
            if isinstance(current, ast.Attribute):
                current = current.value
            else:
                break
        return self._get_var_name(current)

    def _get_source(self, node: ast.AST) -> str:
        """Get source code for an AST node using line numbers."""
        try:
            return ast.get_source_segment(self.source_code, node) or ""
        except Exception:
            return ""

    def _get_source_from_node(self, node: ast.AST) -> str:
        """Get source code for an AST node."""
        try:
            return ast.get_source_segment(self.source_code, node) or ""
        except Exception:
            return ""

    def _get_first_arg_str(self, call_node: ast.Call) -> Optional[str]:
        if call_node.args:
            arg = call_node.args[0]
            if isinstance(arg, ast.Constant):
                return repr(arg.value)
            if isinstance(arg, ast.List):
                items = []
                for elt in arg.elts:
                    if isinstance(elt, ast.Constant):
                        items.append(repr(elt.value))
                return ", ".join(items) if items else None
            return self._get_source_from_node(arg)
        return None

    def _get_keyword_str(self, call_node: ast.Call, keyword: str) -> Optional[str]:
        for kw in call_node.keywords:
            if kw.arg == keyword:
                if isinstance(kw.value, ast.Constant):
                    return str(kw.value.value)
                if isinstance(kw.value, ast.List):
                    items = []
                    for elt in kw.value.elts:
                        if isinstance(elt, ast.Constant):
                            items.append(str(elt.value))
                    return ", ".join(items)
                return self._get_source_from_node(kw.value)
        return None

    @staticmethod
    def _truncate(s: str, max_len: int) -> str:
        if not s:
            return ""
        s = s.strip().replace("\n", " ")
        return s[:max_len] + "…" if len(s) > max_len else s

"""Risk classifier — AST-based analysis of Python ETL scripts.

Classifies scripts as Low, Medium, or High Risk based on the security
and complexity of their operations.
"""

import ast

class RiskClassifier:
    """AST-based risk engine to evaluate ETL scripts."""

    HIGH_RISK_CALLS = {
        "subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_output",
        "os.system", "os.popen", "os.spawn", "shutil.rmtree", "eval", "exec", "__import__",
        "getattr", "setattr", "globals", "locals", "compile", "dir", "vars", "delattr", "hasattr"
    }
    
    HIGH_RISK_METHODS = {"to_sql", "to_parquet"}
    MEDIUM_RISK_METHODS = {"read_sql", "apply", "pickle"}

    def __init__(self):
        self.reasons = []
        self.risk_level = "low"
        self.blocked = False

    def add_reason(self, level: str, msg: str):
        self.reasons.append(msg)
        if level == "high":
            self.risk_level = "high"
            self.blocked = True
        elif level == "medium" and self.risk_level != "high":
            self.risk_level = "medium"

    def classify(self, code: str) -> dict:
        """Analyze the source code AST and return a risk classification dict."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "level": "high",
                "reasons": [f"Syntax error prevents classification at line {e.lineno}: {e.msg}"],
                "blocked": True
            }

        # Reset states
        self.reasons = []
        self.risk_level = "low"
        self.blocked = False

        visitor = RiskVisitor(self)
        visitor.visit(tree)

        return {
            "level": self.risk_level,
            "reasons": self.reasons,
            "blocked": self.blocked
        }


class RiskVisitor(ast.NodeVisitor):
    """AST visitor to detect dangerous imports, calls, methods, and patterns."""

    def __init__(self, classifier: RiskClassifier):
        self.classifier = classifier
        self.merge_join_count = 0
        self.nesting_depth = 0
        self.max_nesting_depth = 5

    def _enter_nested(self, node: ast.AST):
        self.nesting_depth += 1
        if self.nesting_depth > self.max_nesting_depth:
            lineno = getattr(node, "lineno", 0)
            self.classifier.add_reason(
                "medium",
                f"Highly nested code structure (nesting depth {self.nesting_depth} exceeds limit of {self.max_nesting_depth}) at line {lineno}"
            )

    def _exit_nested(self):
        self.nesting_depth -= 1

    def visit_For(self, node: ast.For):
        self._enter_nested(node)
        self.generic_visit(node)
        self._exit_nested()

    def visit_While(self, node: ast.While):
        self._enter_nested(node)

        # Detect endless loops (e.g. while True:, while 1:)
        is_endless = False
        if isinstance(node.test, ast.Constant):
            if node.test.value is True or node.test.value == 1:
                is_endless = True
        elif isinstance(node.test, ast.Name) and node.test.id == "True":
            is_endless = True

        if is_endless:
            # Check for a Break node inside the loop block
            has_break = False
            for child in ast.walk(node):
                if isinstance(child, ast.Break):
                    has_break = True
                    break
            if not has_break:
                lineno = getattr(node, "lineno", 0)
                self.classifier.add_reason(
                    "high",
                    f"Infinite loop structure 'while True' without exit break detected at line {lineno}"
                )

        self.generic_visit(node)
        self._exit_nested()

    def visit_If(self, node: ast.If):
        self._enter_nested(node)
        self.generic_visit(node)
        self._exit_nested()

    def visit_With(self, node: ast.With):
        self._enter_nested(node)
        self.generic_visit(node)
        self._exit_nested()

    def visit_Try(self, node: ast.Try):
        self._enter_nested(node)
        self.generic_visit(node)
        self._exit_nested()

    def visit_Attribute(self, node: ast.Attribute):
        # Prevent access to dunder/private attributes (e.g., obj.__code__)
        if node.attr.startswith("__") and node.attr.endswith("__"):
            lineno = getattr(node, "lineno", 0)
            self.classifier.add_reason(
                "high",
                f"Access to private/dunder attribute '{node.attr}' detected at line {lineno}"
            )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for name in node.names:
            alias = name.name.split(".")[0]
            if alias in {"subprocess", "socket", "requests"}:
                self.classifier.add_reason(
                    "high", f"Import of dangerous module '{name.name}' at line {node.lineno}"
                )
            elif alias in {"pickle"}:
                self.classifier.add_reason(
                    "medium", f"Import of module '{name.name}' (pickle operations) at line {node.lineno}"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            root_mod = node.module.split(".")[0]
            if root_mod in {"subprocess", "socket", "requests"}:
                self.classifier.add_reason(
                    "high", f"Import from dangerous module '{node.module}' at line {node.lineno}"
                )
            elif root_mod in {"pickle"}:
                self.classifier.add_reason(
                    "medium", f"Import from module '{node.module}' at line {node.lineno}"
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        func_name = self._resolve_func_name(node.func)
        lineno = getattr(node, "lineno", 0)

        # 1. Dangerous Functions (eval, exec, subprocess, etc.)
        if func_name in self.classifier.HIGH_RISK_CALLS:
            self.classifier.add_reason(
                "high", f"Contains '{func_name}()' call at line {lineno}"
            )
        
        # 2. open() with write mode
        elif func_name == "open":
            is_write = False
            # Check positional arguments
            if len(node.args) >= 2:
                mode_arg = node.args[1]
                if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
                    if any(c in mode_arg.value for c in "wax+"):
                        is_write = True
            # Check keyword arguments
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    if any(c in kw.value.value for c in "wax+"):
                        is_write = True
            if is_write:
                self.classifier.add_reason(
                    "high", f"Contains 'open()' with write/append mode at line {lineno}"
                )

        # 3. Method calls (to_sql, to_parquet, apply, read_sql)
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            if method_name in self.classifier.HIGH_RISK_METHODS:
                self.classifier.add_reason(
                    "high", f"Contains dataframe '{method_name}()' write at line {lineno}"
                )
            elif method_name in self.classifier.MEDIUM_RISK_METHODS:
                if method_name == "apply":
                    # Check if using lambda inside apply
                    uses_lambda = False
                    if len(node.args) >= 1 and isinstance(node.args[0], ast.Lambda):
                        uses_lambda = True
                    for kw in node.keywords:
                        if kw.arg == "func" and isinstance(kw.value, ast.Lambda):
                            uses_lambda = True
                    if uses_lambda:
                        self.classifier.add_reason(
                            "medium", f"Contains custom '.apply(lambda ...)' transformation at line {lineno}"
                        )
                else:
                    self.classifier.add_reason(
                        "medium", f"Contains dataframe '{method_name}()' operation at line {lineno}"
                    )

            # Count merges and joins to flag complex workflows
            if method_name in {"merge", "join", "concat"}:
                self.merge_join_count += 1
                if self.merge_join_count >= 3:
                    self.classifier.add_reason(
                        "medium", f"Complex workflow detected (3+ join/merge operations) by line {lineno}"
                    )

        # 4. Check for dynamic SQL query vulnerabilities in database query methods
        is_sql_query_func = any(x in func_name.lower() for x in ["read_sql", "execute", "query"])
        if is_sql_query_func and node.args:
            sql_arg = node.args[0]
            is_dynamic_sql = False
            
            # Case A: f-string
            if isinstance(sql_arg, ast.JoinedStr):
                is_dynamic_sql = True
            # Case B: modulo operator (e.g. "SELECT..." % val)
            elif isinstance(sql_arg, ast.BinOp) and isinstance(sql_arg.op, ast.Mod):
                if isinstance(sql_arg.left, ast.Constant) and isinstance(sql_arg.left.value, str):
                    is_dynamic_sql = True
            # Case C: .format() call
            elif isinstance(sql_arg, ast.Call) and isinstance(sql_arg.func, ast.Attribute):
                if sql_arg.func.attr == "format":
                    if isinstance(sql_arg.func.value, ast.Constant) and isinstance(sql_arg.func.value.value, str):
                        is_dynamic_sql = True
                    elif isinstance(sql_arg.func.value, ast.Name):
                        is_dynamic_sql = True

            if is_dynamic_sql:
                self.classifier.add_reason(
                    "high",
                    f"Dynamic SQL query construction (vulnerable to SQL injection) detected at line {lineno}. Use query parameters instead."
                )

        # Check for path traversals (e.g. read_csv('../data.csv'))
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if ".." in arg.value:
                    self.classifier.add_reason(
                        "medium", f"External path traversal '{arg.value}' detected at line {lineno}"
                    )

        self.generic_visit(node)

    def _resolve_func_name(self, node) -> str:
        """Resolve func name representation for simple cases (e.g. subprocess.run)."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            left = self._resolve_func_name(node.value)
            if left:
                return f"{left}.{node.attr}"
            return node.attr
        return ""

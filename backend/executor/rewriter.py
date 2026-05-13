"""Instrument ast.Module using parser injection_steps (mutates tree in place)."""

from __future__ import annotations

import ast
import copy
import os
from typing import Optional

from parser.operations import READ_OPS, WRITE_OPS


def _start_step(node_id: str) -> ast.Expr:
    return ast.Expr(
        value=ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="_rsli_ctx", ctx=ast.Load()),
                attr="start_step",
                ctx=ast.Load(),
            ),
            args=[ast.Constant(node_id)],
            keywords=[],
        )
    )


def _snapshot(node_id: str, method: str, var_name: str) -> ast.Expr:
    return ast.Expr(
        value=ast.Call(
            func=ast.Name(id="_rsli_snapshot", ctx=ast.Load()),
            args=[
                ast.Constant(node_id),
                ast.Constant(method),
                ast.Name(id=var_name, ctx=ast.Load()),
                ast.Name(id="_rsli_ctx", ctx=ast.Load()),
            ],
            keywords=[],
        ),
    )


def _patch_read_path(
    call: ast.Call,
    abs_path: Optional[str],
) -> ast.Call:
    c = copy.deepcopy(call)
    if not abs_path or not c.args:
        return c
    c.args[0] = ast.Constant(abs_path)
    return c


def _patch_write_path(call: ast.Call, out_dir: str) -> ast.Call:
    c = copy.deepcopy(call)
    if not c.args:
        return c
    orig = c.args[0]
    if isinstance(orig, ast.Constant) and isinstance(orig.value, str):
        base = os.path.basename(orig.value)
    else:
        base = "output.bin"
    c.args[0] = ast.Constant(os.path.join(out_dir, base))
    return c


def _method_name(call: ast.Call) -> Optional[str]:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return None


def _is_read(call: ast.Call) -> bool:
    m = _method_name(call)
    return m in READ_OPS if m else False


def _is_write(call: ast.Call) -> bool:
    m = _method_name(call)
    return m in WRITE_OPS if m else False


def _replace_call_receiver(call: ast.Call, new_recv: ast.expr) -> ast.Call:
    c = copy.deepcopy(call)
    if isinstance(c.func, ast.Attribute):
        c.func = ast.Attribute(value=new_recv, attr=c.func.attr, ctx=ast.Load())
    return c


def _locate_stmt(module: ast.Module, target: ast.stmt) -> tuple[list[ast.stmt], int] | None:
    """Return (body_list, index) for a direct child stmt container."""

    def search_body(body: list[ast.stmt]) -> tuple[list[ast.stmt], int] | None:
        for i, s in enumerate(body):
            if s is target:
                return body, i
            inner = _search_in_stmt(s, target)
            if inner:
                return inner
        return None

    return search_body(module.body)


def _search_in_stmt(s: ast.stmt, target: ast.stmt) -> tuple[list[ast.stmt], int] | None:
    if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for body in (s.body,):
            for i, ch in enumerate(body):
                if ch is target:
                    return body, i
                inner = _search_in_stmt(ch, target)
                if inner:
                    return inner
    if isinstance(s, ast.If):
        for body in (s.body, s.orelse):
            r = _locate_in_body_list(body, target)
            if r:
                return r
    if isinstance(s, (ast.For, ast.While)):
        r = _locate_in_body_list(s.body, target)
        if r:
            return r
        r = _locate_in_body_list(getattr(s, "orelse", []) or [], target)
        if r:
            return r
    if isinstance(s, ast.With):
        return _locate_in_body_list(s.body, target)
    if isinstance(s, ast.Try):
        r = _locate_in_body_list(s.body, target)
        if r:
            return r
        for h in s.handlers:
            r = _locate_in_body_list(h.body, target)
            if r:
                return r
        r = _locate_in_body_list(s.orelse, target)
        if r:
            return r
        r = _locate_in_body_list(s.finalbody, target)
        if r:
            return r
    return None


def _locate_in_body_list(body: list[ast.stmt], target: ast.stmt) -> tuple[list[ast.stmt], int] | None:
    for i, ch in enumerate(body):
        if ch is target:
            return body, i
        inner = _search_in_stmt(ch, target)
        if inner:
            return inner
    return None


def instrument_module(
    module: ast.Module,
    injection_steps: list[dict],
    upload_by_node_id: dict[str, str],
    output_dir: str,
) -> None:
    """Mutate module: insert start_step + snapshot; patch read/write paths."""
    by_parent: dict[int, list[dict]] = {}
    for st in injection_steps:
        pid = id(st["parent_stmt"])
        by_parent.setdefault(pid, []).append(st)

    order = {id(s): i for i, s in enumerate(injection_steps)}
    for pid, steps in by_parent.items():
        steps.sort(key=lambda s: order[id(s)])

    for pid, steps in by_parent.items():
        parent = steps[0]["parent_stmt"]
        loc = _locate_stmt(module, parent)
        if not loc:
            continue
        body, idx = loc
        new_block = _expand_parent_stmt(parent, steps, upload_by_node_id, output_dir)
        body[idx : idx + 1] = new_block


def _expand_parent_stmt(
    parent: ast.stmt,
    steps: list[dict],
    upload_by_node_id: dict[str, str],
    output_dir: str,
) -> list[ast.stmt]:
    steps = list(steps)  # same order as parse (inner chain first)

    if isinstance(parent, ast.Assign):
        if len(steps) == 1 and steps[0].get("call_node") is not None:
            st0 = steps[0]
            call = st0["call_node"]
            call_p = copy.deepcopy(call)
            cat = st0.get("category", "")
            if cat == "source" and _is_read(call):
                path = upload_by_node_id.get(st0["node_id"])
                if path:
                    call_p = _patch_read_path(call_p, path)
            elif cat == "target" and _is_write(call):
                call_p = _patch_write_path(call_p, output_dir)
            new_assign = ast.Assign(targets=parent.targets, value=call_p, lineno=parent.lineno, col_offset=parent.col_offset)
            return [
                _start_step(st0["node_id"]),
                new_assign,
                _snapshot(st0["node_id"], st0["method"], st0["snapshot_var"]),
            ]
        if len(steps) == 1 and steps[0].get("call_node") is None:
            st0 = steps[0]
            if st0["method"] == "column_assign":
                return [
                    _start_step(st0["node_id"]),
                    copy.deepcopy(parent),
                    _snapshot(st0["node_id"], st0["method"], st0["snapshot_var"]),
                ]
            if st0["method"] == "boolean_index":
                return [
                    _start_step(st0["node_id"]),
                    copy.deepcopy(parent),
                    _snapshot(st0["node_id"], st0["method"], st0["snapshot_var"]),
                ]
        # multi-step chain on one assign
        return _flatten_chain_assign(parent, steps, upload_by_node_id, output_dir)

    if isinstance(parent, ast.Expr) and isinstance(parent.value, ast.Call):
        st0 = steps[0]
        if len(steps) != 1:
            return [parent]  # unsupported
        call = parent.value
        call_p = copy.deepcopy(call)
        cat = st0.get("category", "")
        if cat == "source" and _is_read(call):
            path = upload_by_node_id.get(st0["node_id"])
            if path:
                call_p = _patch_read_path(call_p, path)
        elif cat == "target" and _is_write(call):
            call_p = _patch_write_path(call_p, output_dir)
        expr = ast.Expr(value=call_p, lineno=parent.lineno, col_offset=parent.col_offset)
        return [
            _start_step(st0["node_id"]),
            expr,
            _snapshot(st0["node_id"], st0["method"], st0["snapshot_var"]),
        ]

    return [parent]


def _flatten_chain_assign(
    assign: ast.Assign,
    steps: list[dict],
    upload_by_node_id: dict[str, str],
    output_dir: str,
) -> list[ast.stmt]:
    out: list[ast.stmt] = []
    prev_name: Optional[str] = None
    for i, st in enumerate(steps):
        call = st["call_node"]
        if not isinstance(call, ast.Call):
            return [assign]
        is_last = i == len(steps) - 1
        snap_var = st["snapshot_var"]
        call_p = copy.deepcopy(call)
        cat = st.get("category", "")
        if cat == "source" and _is_read(call):
            path = upload_by_node_id.get(st["node_id"])
            if path:
                call_p = _patch_read_path(call_p, path)
        elif cat == "target" and _is_write(call):
            call_p = _patch_write_path(call_p, output_dir)
        if prev_name is not None:
            call_p = _replace_call_receiver(call_p, ast.Name(id=prev_name, ctx=ast.Load()))

        out.append(_start_step(st["node_id"]))
        if is_last:
            out.append(ast.Assign(targets=assign.targets, value=call_p, lineno=assign.lineno))
        else:
            out.append(
                ast.Assign(
                    targets=[ast.Name(id=snap_var, ctx=ast.Store())],
                    value=call_p,
                    lineno=assign.lineno,
                )
            )
        out.append(_snapshot(st["node_id"], st["method"], snap_var))
        prev_name = snap_var
    return out


def unparse_module(module: ast.Module) -> str:
    ast.fix_missing_locations(module)
    return ast.unparse(module)

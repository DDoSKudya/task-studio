#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TUTOR = ROOT / "services" / "tutor"
if str(TUTOR) not in sys.path:
    sys.path.insert(0, str(TUTOR))


def _gold(path: Path):
    from app.domain.course_adapters.gold import GoldStore

    return GoldStore(path)


def _role(raw: str):
    from app.domain.course_adapters.roles import parse_role

    role = parse_role(raw)
    if role is None:
        raise SystemExit(f"unknown role {raw}")
    return role


def _report_from_path(path: Path):
    from app.domain.course_adapters.evaluate import report_from_dict

    return report_from_dict(json.loads(path.read_text(encoding="utf-8")))


def cmd_eval(args: argparse.Namespace) -> int:
    from app.domain.course_adapters.eval_corpus import eval_article_count
    from app.domain.course_adapters.evaluate import compiler_baseline

    report = compiler_baseline()
    args.out.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    sys.stdout.write(
        f"compiler baseline mean={report.mean:.3f} "
        f"on {report.article_count}/{eval_article_count()} articles\n"
    )
    return 0


def cmd_harvest(args: argparse.Namespace) -> int:
    from app.domain.course_adapters.gold import harvest_from_build
    from app.domain.course_build import CourseBuildStore

    store = CourseBuildStore(args.builds, ttl_days=30)
    written = harvest_from_build(
        store,
        _gold(args.gold),
        user_id=uuid.UUID(args.user),
        build_id=uuid.UUID(args.build),
        source=args.source,
    )
    sys.stdout.write(f"harvested={written}\n")
    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    from app.domain.course_adapters.export import prepare_train_job

    job = prepare_train_job(_gold(args.gold), _role(args.role), workdir=args.workdir)
    sys.stdout.write(f"dataset={job.dataset_path}\nscript={job.script_path}\n")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    from app.domain.course_adapters.export import TrainJob, export_gguf_to_ollama
    from app.domain.course_adapters.roles import ollama_model_for_role

    role = _role(args.role)
    job = TrainJob(
        role=role,
        dataset_path=args.workdir / role / "dataset.jsonl",
        script_path=args.workdir / role / "train_qlora.py",
        output_dir=args.workdir / role,
        base_model="unsloth/Qwen2.5-7B-Instruct",
        ollama_name=ollama_model_for_role(role),
        quantization="q4_k_m",
        gguf_dir=args.workdir / role / "gguf",
    )
    name = export_gguf_to_ollama(job, gguf_file=args.gguf)
    sys.stdout.write(f"ollama model={name}\n")
    return 0


def cmd_ship(args: argparse.Namespace) -> int:
    from app.domain.course_adapters.ship import ship_adapter

    role = _role(args.role)
    book = ship_adapter(
        role=role,
        adapter=_report_from_path(args.adapter),
        compiler=_report_from_path(args.compiler),
        registry_path=args.registry,
    )
    entry = book.shipped(role)
    if entry is None:
        sys.stderr.write(f"ship did not record {role}\n")
        return 1
    sys.stdout.write(f"shipped {entry.role} model={entry.model} mean={entry.eval_mean:.3f}\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    eval_p = sub.add_parser("eval", help="compiler baseline on 20 articles")
    eval_p.add_argument("--out", type=Path, default=Path("compiler-baseline.json"))
    eval_p.set_defaults(func=cmd_eval)

    harvest_p = sub.add_parser("harvest", help="copy gold from a course build before discard")
    harvest_p.add_argument("--builds", type=Path, required=True)
    harvest_p.add_argument("--gold", type=Path, required=True)
    harvest_p.add_argument("--user", required=True)
    harvest_p.add_argument("--build", required=True)
    harvest_p.add_argument("--source", default="local")
    harvest_p.set_defaults(func=cmd_harvest)

    prep = sub.add_parser("prepare", help="write dataset + Unsloth script; refuses without gold")
    prep.add_argument("--role", required=True)
    prep.add_argument("--gold", type=Path, required=True)
    prep.add_argument("--workdir", type=Path, required=True)
    prep.set_defaults(func=cmd_prepare)

    exp = sub.add_parser("export", help="ollama create from GGUF")
    exp.add_argument("--role", required=True)
    exp.add_argument("--workdir", type=Path, required=True)
    exp.add_argument("--gguf", type=Path, default=None)
    exp.set_defaults(func=cmd_export)

    ship_p = sub.add_parser("ship", help="stamp registry if adapter beats compiler")
    ship_p.add_argument("--role", required=True)
    ship_p.add_argument("--adapter", type=Path, required=True)
    ship_p.add_argument("--compiler", type=Path, required=True)
    ship_p.add_argument("--registry", type=Path, required=True)
    ship_p.set_defaults(func=cmd_ship)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .gold import GoldStore, assert_gold_ready
from .roles import AdapterRefused, AdapterRole, ollama_model_for_role

CommandRunner = Callable[[Sequence[str], Path], None]

_UNSLOTH_SCRIPT = '''\
"""QLoRA → GGUF for one course adapter. Run on a GPU host, not inside tutor."""
from datasets import load_dataset
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name={base!r},
    max_seq_length=4096,
    load_in_4bit=True,
)
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    use_gradient_checkpointing="unsloth",
)
dataset = load_dataset("json", data_files={dataset!r}, split="train")

def to_text(row):
    return (
        row["system"]
        + "\\n\\n"
        + row["user"]
        + "\\n\\n"
        + row["assistant"]
    )

dataset = dataset.map(lambda row: {{"text": to_text(row)}})
from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    args=TrainingArguments(
        output_dir={work!r},
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        max_steps=120,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        report_to=[],
    ),
)
trainer.train()
model.save_pretrained_gguf({gguf_dir!r}, tokenizer, quantization_method={quant!r})
'''


@dataclass(frozen=True, slots=True)
class TrainJob:
    role: AdapterRole
    dataset_path: Path
    script_path: Path
    output_dir: Path
    base_model: str
    ollama_name: str
    quantization: str
    gguf_dir: Path


def write_dataset(gold: GoldStore, role: AdapterRole, dest: Path) -> Path:
    pairs = gold.load(role)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as handle:
        for pair in pairs:
            handle.write(
                json.dumps(
                    {
                        "system": pair.system,
                        "user": pair.user,
                        "assistant": pair.assistant,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return dest


def write_modelfile(*, from_ref: str) -> str:
    return f"FROM {from_ref}\nPARAMETER temperature 0\nPARAMETER num_ctx 4096\n"


def default_runner(command: Sequence[str], workdir: Path) -> None:
    subprocess.run(list(command), cwd=str(workdir), check=True)


def ollama_create(
    name: str,
    modelfile: str,
    *,
    workdir: Path,
    runner: CommandRunner | None = None,
) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    path = workdir / "Modelfile"
    path.write_text(modelfile, encoding="utf-8")
    create = runner or default_runner
    create(["ollama", "create", name, "-f", str(path)], workdir)


def prepare_train_job(
    gold: GoldStore,
    role: AdapterRole,
    *,
    workdir: Path,
    base_model: str = "unsloth/Qwen2.5-7B-Instruct",
    quantization: str = "q4_k_m",
    min_pairs: int | None = None,
) -> TrainJob:
    assert_gold_ready(gold, role, min_pairs=min_pairs)
    output_dir = workdir / role
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = write_dataset(gold, role, output_dir / "dataset.jsonl")
    gguf_dir = output_dir / "gguf"
    script_path = output_dir / "train_qlora.py"
    script_path.write_text(
        _UNSLOTH_SCRIPT.format(
            base=base_model,
            dataset=str(dataset_path),
            work=str(output_dir / "sft"),
            gguf_dir=str(gguf_dir),
            quant=quantization,
        ),
        encoding="utf-8",
    )
    return TrainJob(
        role=role,
        dataset_path=dataset_path,
        script_path=script_path,
        output_dir=output_dir,
        base_model=base_model,
        ollama_name=ollama_model_for_role(role),
        quantization=quantization,
        gguf_dir=gguf_dir,
    )


def export_gguf_to_ollama(
    job: TrainJob,
    *,
    gguf_file: Path | None = None,
    runner: CommandRunner | None = None,
) -> str:
    gguf = gguf_file
    if gguf is None:
        if candidates := sorted(job.gguf_dir.glob("*.gguf")):
            gguf = candidates[0]
        else:
            raise AdapterRefused(
                f"no GGUF in {job.gguf_dir}; run {job.script_path} on a GPU host first"
            )
    if not gguf.is_file():
        raise AdapterRefused(f"missing GGUF {gguf}")
    ollama_create(
        job.ollama_name,
        write_modelfile(from_ref=str(gguf.resolve())),
        workdir=job.output_dir,
        runner=runner,
    )
    return job.ollama_name

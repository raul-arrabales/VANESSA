from __future__ import annotations

import os
from pathlib import Path
import subprocess
import textwrap


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _make_fake_bin(tmp_path: Path) -> Path:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    _write_executable(
        fake_bin / "docker",
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json
            import os
            import sys

            args = sys.argv[1:]
            if args[:2] == ["compose", "version"]:
                sys.exit(0)
            if len(args) >= 2 and args[0] == "compose" and "exec" in args:
                exec_index = args.index("exec")
                service_index = exec_index + 1
                if args[service_index] == "-T":
                    service_index += 1
                service_name = args[service_index]
                command = args[service_index + 1 :]
                joined = " ".join(command)

                if service_name == "postgres" and command and command[0] == "psql":
                    print(
                        "\\t".join(
                            [
                                os.environ.get("FAKE_SLOT_MANAGED_MODEL_ID", ""),
                                os.environ.get("FAKE_SLOT_RUNTIME_MODEL_ID", ""),
                                os.environ.get("FAKE_SLOT_LOCAL_PATH", ""),
                            ]
                        )
                    )
                    sys.exit(0)

                if service_name in {"llm_runtime_inference", "llm_runtime_embeddings"} and "/health" in joined:
                    sys.exit(0)

                if service_name == "llm_runtime_embeddings" and "/v1/models" in joined:
                    value = os.environ.get("FAKE_LLM_RUNTIME_EMBEDDINGS_IDS", "")
                    for item in value.split(","):
                        item = item.strip()
                        if item:
                            print(item)
                    sys.exit(0)

                if service_name == "llm_runtime_embeddings" and "/v1/admin/runtime-state" in joined:
                    payload = os.environ.get("FAKE_LLM_RUNTIME_EMBEDDINGS_RUNTIME_STATE_JSON", "")
                    if payload:
                        parsed = json.loads(payload)
                        print(
                            "\\t".join(
                                [
                                    str(parsed.get("load_state") or "").strip(),
                                    str(parsed.get("runtime_model_id") or "").strip(),
                                    str(parsed.get("managed_model_id") or "").strip(),
                                    str(parsed.get("local_path") or "").strip(),
                                    str(parsed.get("last_error") or "").strip(),
                                ]
                            )
                        )
                        sys.exit(0)
                    sys.exit(1)

                if service_name == "llm" and "/v1/models" in joined:
                    value = os.environ.get("FAKE_LLM_EMBEDDINGS_IDS", "")
                    for item in value.split(","):
                        item = item.strip()
                        if item:
                            print(item)
                    sys.exit(0)

            sys.stderr.write(f"unexpected docker invocation: {' '.join(sys.argv[1:])}\\n")
            sys.exit(1)
            """
        ),
    )
    _write_executable(
        fake_bin / "curl",
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import sys

            args = sys.argv[1:]
            url = args[-1]
            if "-w" in args:
                sys.stdout.write("401")
                sys.exit(0)
            if url.endswith("/v1/models"):
                sys.stdout.write('{"object":"list","data":[{"id":"dummy","capabilities":{"text":true,"embeddings":false}}]}')
                sys.exit(0)
            sys.stdout.write("{}")
            sys.exit(0)
            """
        ),
    )
    _write_executable(fake_bin / "nc", "#!/usr/bin/env bash\nexit 0\n")
    _write_executable(
        fake_bin / "lscpu",
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            cat <<'EOF'
            Architecture:                         x86_64
            Flags:                                fpu vme de pse tsc msr pae mce cx8 apic sep mtrr avx2
            EOF
            """
        ),
    )
    return fake_bin


def _run_health(tmp_path: Path, **env_overrides: str) -> subprocess.CompletedProcess[str]:
    fake_bin = _make_fake_bin(tmp_path)

    repo_root = Path(__file__).resolve().parents[2]
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "LLM_ROUTING_MODE": "local_only",
        "LLM_RUNTIME_ACCELERATOR": "cpu",
        "LLM_RUNTIME_CPU_VARIANT": "avx2",
        "FAKE_SLOT_MANAGED_MODEL_ID": "sentence-transformers--all-MiniLM-L6-v2",
        "FAKE_SLOT_RUNTIME_MODEL_ID": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
        "FAKE_SLOT_LOCAL_PATH": "/models/llm/sentence-transformers--all-MiniLM-L6-v2",
        "FAKE_LLM_RUNTIME_EMBEDDINGS_RUNTIME_STATE_JSON": '{"load_state":"empty","runtime_model_id":"","managed_model_id":"","local_path":"","last_error":""}',
        "FAKE_LLM_RUNTIME_EMBEDDINGS_IDS": "",
        "FAKE_LLM_EMBEDDINGS_IDS": "",
        **env_overrides,
    }

    return subprocess.run(
        ["bash", "ops/local-staging/health.sh"],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_health_script_fails_when_embeddings_slot_is_persisted_but_runtime_is_empty(tmp_path: Path):
    result = _run_health(tmp_path)

    assert result.returncode == 3
    assert "llm_runtime_embeddings: OK" in result.stdout
    assert "llm_runtime_embeddings_slot: FAIL" in result.stdout
    assert "persisted slot 'sentence-transformers--all-MiniLM-L6-v2' is not loaded into llm_runtime_embeddings" in result.stdout


def test_health_script_waits_when_embeddings_slot_is_loading(tmp_path: Path):
    result = _run_health(
        tmp_path,
        FAKE_LLM_RUNTIME_EMBEDDINGS_RUNTIME_STATE_JSON='{"load_state":"loading","runtime_model_id":"/models/llm/sentence-transformers--all-MiniLM-L6-v2","managed_model_id":"sentence-transformers--all-MiniLM-L6-v2","local_path":"/models/llm/sentence-transformers--all-MiniLM-L6-v2","last_error":""}',
    )

    assert result.returncode == 0
    assert "llm_runtime_embeddings_slot: WAIT" in result.stdout
    assert "persisted slot 'sentence-transformers--all-MiniLM-L6-v2' is loading in llm_runtime_embeddings" in result.stdout


def test_health_script_waits_when_embeddings_slot_is_reconciling(tmp_path: Path):
    result = _run_health(
        tmp_path,
        FAKE_LLM_RUNTIME_EMBEDDINGS_RUNTIME_STATE_JSON='{"load_state":"reconciling","runtime_model_id":"/models/llm/sentence-transformers--all-MiniLM-L6-v2","managed_model_id":"sentence-transformers--all-MiniLM-L6-v2","local_path":"/models/llm/sentence-transformers--all-MiniLM-L6-v2","last_error":""}',
    )

    assert result.returncode == 0
    assert "llm_runtime_embeddings_slot: WAIT" in result.stdout
    assert "persisted slot 'sentence-transformers--all-MiniLM-L6-v2' is reconciling in llm_runtime_embeddings" in result.stdout


def test_health_script_fails_when_runtime_reports_loaded_but_model_inventory_is_missing(tmp_path: Path):
    result = _run_health(
        tmp_path,
        FAKE_LLM_RUNTIME_EMBEDDINGS_RUNTIME_STATE_JSON='{"load_state":"loaded","runtime_model_id":"/models/llm/sentence-transformers--all-MiniLM-L6-v2","managed_model_id":"sentence-transformers--all-MiniLM-L6-v2","local_path":"/models/llm/sentence-transformers--all-MiniLM-L6-v2","last_error":""}',
    )

    assert result.returncode == 3
    assert "llm_runtime_embeddings_slot: FAIL" in result.stdout
    assert "persisted slot 'sentence-transformers--all-MiniLM-L6-v2' is not loaded into llm_runtime_embeddings" in result.stdout


def test_health_script_fails_when_llm_is_missing_embeddings_advertisement_after_runtime_load(tmp_path: Path):
    result = _run_health(
        tmp_path,
        FAKE_LLM_RUNTIME_EMBEDDINGS_RUNTIME_STATE_JSON='{"load_state":"loaded","runtime_model_id":"/models/llm/sentence-transformers--all-MiniLM-L6-v2","managed_model_id":"sentence-transformers--all-MiniLM-L6-v2","local_path":"/models/llm/sentence-transformers--all-MiniLM-L6-v2","last_error":""}',
        FAKE_LLM_RUNTIME_EMBEDDINGS_IDS="/models/llm/sentence-transformers--all-MiniLM-L6-v2",
    )

    assert result.returncode == 3
    assert "llm_runtime_embeddings_slot: FAIL" in result.stdout
    assert "llm does not advertise any embeddings-capable models" in result.stdout

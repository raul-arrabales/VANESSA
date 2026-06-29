from __future__ import annotations

from typing import Any

WORKFLOW_AGENT_TYPE = "workflow"

DEFAULT_RETRIEVAL_CONTEXT_PROMPT = "\n".join(
    [
        "Use the following retrieved context if it is relevant to the user's request.",
        "When you use retrieved context, cite the supporting reference inline with bracketed numeric citations such as [1] or [1, 2].",
        "Do not cite a reference unless it supports the sentence that uses the citation.",
    ]
)

DEFAULT_WORKFLOW_INPUT_EXTRACTION_PROMPT = "\n".join(
    [
        "Inspect the workflow conversation and populate the required workflow variables from user-provided information.",
        "Use the workflow variable context exactly as provided, including variable names, types, labels, guidance, and current values.",
        "When the prompt references a token such as {{user_name}}, treat it as the workflow variable named user_name.",
        "Return only JSON with complete:boolean, variables:object, missing:array, question:string.",
    ]
)

DEFAULT_WORKFLOW_TOOL_ARGUMENTS_PROMPT = "\n".join(
    [
        "Create schema-valid MCP tool arguments for the current workflow action.",
        "Use the workflow variable context exactly as provided, including variable names, types, labels, guidance, and current values.",
        "When the prompt references a token such as {{user_name}}, treat it as the workflow variable named user_name.",
        "Return only a JSON object that matches the tool input schema.",
    ]
)

DEFAULT_WORKFLOW_OUTPUT_RESPONSE_PROMPT = "\n".join(
    [
        "Compose the final workflow chat response for the user.",
        "Use the workflow variable context exactly as provided, including variable names, types, labels, guidance, and current values.",
        "When the prompt references a token such as {{user_name}}, treat it as the workflow variable named user_name.",
        "Return only JSON with response:string.",
    ]
)


def default_agent_runtime_prompts() -> dict[str, str]:
    return {
        "retrieval_context": DEFAULT_RETRIEVAL_CONTEXT_PROMPT,
        "workflow_input_extraction": DEFAULT_WORKFLOW_INPUT_EXTRACTION_PROMPT,
        "workflow_tool_arguments": DEFAULT_WORKFLOW_TOOL_ARGUMENTS_PROMPT,
        "workflow_output_response": DEFAULT_WORKFLOW_OUTPUT_RESPONSE_PROMPT,
    }


def default_runtime_prompts_for_agent_type(agent_type: Any) -> dict[str, str]:
    normalized_agent_type = str(agent_type or "").strip().lower()
    if normalized_agent_type == WORKFLOW_AGENT_TYPE:
        return {
            "retrieval_context": "",
            "workflow_input_extraction": DEFAULT_WORKFLOW_INPUT_EXTRACTION_PROMPT,
            "workflow_tool_arguments": DEFAULT_WORKFLOW_TOOL_ARGUMENTS_PROMPT,
            "workflow_output_response": DEFAULT_WORKFLOW_OUTPUT_RESPONSE_PROMPT,
        }
    return default_agent_runtime_prompts()


def normalize_agent_runtime_prompts(value: Any, *, agent_type: Any = None) -> dict[str, str]:
    runtime_prompts = value if isinstance(value, dict) else {}
    defaults = default_runtime_prompts_for_agent_type(agent_type)
    return {
        "retrieval_context": str(runtime_prompts.get("retrieval_context") or defaults["retrieval_context"]).strip(),
        "workflow_input_extraction": str(
            runtime_prompts.get("workflow_input_extraction") or defaults["workflow_input_extraction"]
        ).strip(),
        "workflow_tool_arguments": str(
            runtime_prompts.get("workflow_tool_arguments") or defaults["workflow_tool_arguments"]
        ).strip(),
        "workflow_output_response": str(
            runtime_prompts.get("workflow_output_response") or defaults["workflow_output_response"]
        ).strip(),
    }

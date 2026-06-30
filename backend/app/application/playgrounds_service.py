from __future__ import annotations

from collections.abc import Generator, Iterator, Sequence
from datetime import date
from typing import Any

from ..config import AuthConfig
from ..config import get_auth_config
from ..domain.playgrounds import (
    CHAT_PLAYGROUND_KIND,
    KNOWLEDGE_PLAYGROUND_KIND,
    PLAYGROUND_ASSISTANTS,
    conversation_kind_for_playground_kind,
    default_assistant_ref_for_kind,
    playground_kind_for_conversation_kind,
)
from ..infrastructure import playgrounds_repository
from ..repositories.agent_workflow_runs import get_workflow_run, upsert_workflow_run
from ..services.catalog_errors import CatalogError
from ..services.catalog_service import get_catalog_agent
from ..services.agent_engine_client import AgentEngineClientError
from ..services.chat_inference import (
    chat_completion_stream_with_allowed_model,
    chat_completion_with_allowed_model,
    extract_output_text,
)
from ..services.modelops_common import ModelOpsError
from ..services.modelops_queries import list_model_picker_options
from ..services.chat_attachments import ChatAttachmentError, bind_message_attachments, validate_owned_image_references
from ..services.message_content import MESSAGE_CONTENT_METADATA_KEY, content_text, message_content_parts, normalize_content_parts, text_part
from ..services.platform_service import get_active_platform_runtime
from ..services.platform_types import PlatformControlPlaneError
from ..services.stream_errors import public_stream_error_payload
from ..services.stream_telemetry import (
    STREAM_PHASE_FIRST_TOKEN_DELIVERY,
    STREAM_STATUS_LABEL_OPENING,
    STREAM_STATUS_LABEL_RECEIVED_FIRST_TOKEN,
    STREAM_STATUS_LABEL_SETUP_COMPLETE,
    STREAM_STATUS_LABEL_STREAMED,
    STREAM_STATUS_LABEL_STREAMING,
    STREAM_STATUS_LABEL_WAITING_FIRST_TOKEN,
    TRANSPORT_DETAIL_KEYS,
)
from .playground_execution import (
    PlaygroundExecutionRequest,
    PlaygroundExecutionResult,
    PlaygroundExecutionValidationError,
    auto_title_from_prompt,
    build_context_messages,
    complete_status,
    execute_agent_chat_request,
    execute_knowledge_request,
    list_runtime_knowledge_base_options,
    normalize_prompt,
    public_status,
    serialize_message,
    serialize_datetime,
    start_status,
    string_or_none,
    stream_agent_chat_request,
    stream_knowledge_request,
)

DEFAULT_TITLE_SOURCE = "auto"
DEFAULT_CHAT_TITLE = "New chat session"
DEFAULT_KNOWLEDGE_TITLE = "New knowledge session"
TEMPORARY_CHAT_TITLE = "Temporary chat"
IMAGE_ONLY_EXECUTION_PROMPT = "User sent image attachment(s)."
SESSION_UNSET = playgrounds_repository.UNSET

PlaygroundSessionValidationError = PlaygroundExecutionValidationError
list_knowledge_chat_knowledge_bases = list_runtime_knowledge_base_options


class PlaygroundSessionNotFoundError(Exception):
    pass


class PlaygroundChatExecutionError(RuntimeError):
    def __init__(self, payload: dict[str, Any], status_code: int):
        super().__init__(str(payload.get("message") or payload.get("error") or "playground_chat_failed"))
        self.payload = payload
        self.status_code = status_code


def _record_status(statuses: dict[str, dict[str, Any]], status: dict[str, Any]) -> dict[str, Any]:
    public = public_status(status)
    status_id = str(public.get("id") or "")
    if status_id:
        statuses[status_id] = public
    return public


def _status_values(statuses: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return list(statuses.values())


def _has_image_parts(parts: list[dict[str, Any]]) -> bool:
    return any(str(part.get("type") or "") == "image" for part in parts)


def list_playground_sessions(
    database_url: str,
    *,
    owner_user_id: int,
    playground_kind: str | None = None,
    assistant_ref: str | None = None,
    title_query: str | None = None,
    updated_from: str | None = None,
    updated_to: str | None = None,
) -> list[dict[str, Any]]:
    filters = _normalize_session_filters(
        title_query=title_query,
        updated_from=updated_from,
        updated_to=updated_to,
    )
    if playground_kind:
        conversation_kind = conversation_kind_for_playground_kind(playground_kind)
        rows = playgrounds_repository.list_sessions(
            database_url,
            owner_user_id=owner_user_id,
            conversation_kind=conversation_kind,
            assistant_ref=string_or_none(assistant_ref),
            **filters,
        )
        return [_serialize_session_summary(row) for row in rows]

    items: list[dict[str, Any]] = []
    for conversation_kind in ("plain", "knowledge"):
        rows = playgrounds_repository.list_sessions(
            database_url,
            owner_user_id=owner_user_id,
            conversation_kind=conversation_kind,
            assistant_ref=string_or_none(assistant_ref),
            **filters,
        )
        items.extend(_serialize_session_summary(row) for row in rows)
    items.sort(key=lambda row: row.get("updated_at") or "", reverse=True)
    return items


def create_playground_session(
    database_url: str,
    *,
    owner_user_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    playground_kind = _normalize_playground_kind(payload.get("playground_kind"))
    conversation_kind = conversation_kind_for_playground_kind(playground_kind)
    row = playgrounds_repository.create_session(
        database_url,
        owner_user_id=owner_user_id,
        title=_default_title_for_kind(playground_kind),
        title_source=DEFAULT_TITLE_SOURCE,
        assistant_ref=_normalize_assistant_ref(payload.get("assistant_ref"), playground_kind=playground_kind),
        model_id=_normalize_model_id(payload.get("model_selection", payload.get("model_id"))),
        knowledge_base_id=_normalize_knowledge_base_id(payload.get("knowledge_binding", payload.get("knowledge_base_id"))),
        conversation_kind=conversation_kind,
    )
    _maybe_bootstrap_workflow_session(
        database_url,
        config=get_auth_config(),
        owner_user_id=owner_user_id,
        owner_role="user",
        session_row=row,
    )
    return get_playground_session_detail(
        database_url,
        owner_user_id=owner_user_id,
        session_id=str(row.get("id") or ""),
        playground_kind=playground_kind,
    )


def get_playground_session_detail(
    database_url: str,
    *,
    owner_user_id: int,
    session_id: str,
    playground_kind: str | None = None,
) -> dict[str, Any]:
    row, messages = _load_session_and_messages(
        database_url,
        owner_user_id=owner_user_id,
        session_id=session_id,
        playground_kind=playground_kind,
    )
    return _serialize_session_detail(row, messages)


def update_playground_session(
    database_url: str,
    *,
    owner_user_id: int,
    session_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    row = _require_session(database_url, owner_user_id=owner_user_id, session_id=session_id)
    playground_kind = playground_kind_for_conversation_kind(str(row.get("conversation_kind", "")))
    updated = playgrounds_repository.update_session(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=session_id,
        title=_normalize_title(payload["title"]) if "title" in payload else SESSION_UNSET,
        title_source="manual" if "title" in payload else SESSION_UNSET,
        assistant_ref=_normalize_assistant_ref(payload.get("assistant_ref"), playground_kind=playground_kind) if "assistant_ref" in payload else SESSION_UNSET,
        model_id=_normalize_model_id(payload.get("model_selection", payload.get("model_id"))) if "model_selection" in payload or "model_id" in payload else SESSION_UNSET,
        knowledge_base_id=_normalize_knowledge_base_id(payload.get("knowledge_binding", payload.get("knowledge_base_id"))) if "knowledge_binding" in payload or "knowledge_base_id" in payload else SESSION_UNSET,
        conversation_kind=str(row.get("conversation_kind", "")),
    )
    if updated is None:
        raise PlaygroundSessionNotFoundError
    return _serialize_session_summary(updated)


def delete_playground_session(
    database_url: str,
    *,
    owner_user_id: int,
    session_id: str,
) -> None:
    row = _require_session(database_url, owner_user_id=owner_user_id, session_id=session_id)
    deleted = playgrounds_repository.delete_session(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=session_id,
        conversation_kind=str(row.get("conversation_kind", "")),
    )
    if not deleted:
        raise PlaygroundSessionNotFoundError


def send_playground_message(
    database_url: str,
    *,
    config: AuthConfig,
    request_id: str,
    owner_user_id: int,
    owner_role: str,
    session_id: str,
    prompt: Any,
    content_parts: Any = None,
) -> dict[str, Any]:
    row, history_messages = _load_session_and_messages(
        database_url,
        owner_user_id=owner_user_id,
        session_id=session_id,
        playground_kind=None,
    )
    request = _build_execution_request(
        database_url=database_url,
        owner_user_id=owner_user_id,
        row=row,
        history_messages=history_messages,
        prompt=prompt,
        content_parts=content_parts,
    )
    result = _execute_request(
        database_url,
        config=config,
        request_id=request_id,
        owner_user_id=owner_user_id,
        owner_role=owner_role,
        request=request,
    )
    persisted = _persist_execution_result(
        database_url,
        owner_user_id=owner_user_id,
        request=request,
        result=result,
    )
    session = get_playground_session_detail(
        database_url,
        owner_user_id=owner_user_id,
        session_id=session_id,
        playground_kind=request.playground_kind,
    )
    return _serialize_execution_response(
        session=session,
        persisted=persisted,
        result=result,
    )


def stream_playground_message(
    database_url: str,
    *,
    config: AuthConfig,
    request_id: str,
    owner_user_id: int,
    owner_role: str,
    session_id: str,
    prompt: Any,
    content_parts: Any = None,
) -> Iterator[dict[str, Any]]:
    row, history_messages = _load_session_and_messages(
        database_url,
        owner_user_id=owner_user_id,
        session_id=session_id,
        playground_kind=None,
    )
    request = _build_execution_request(
        database_url=database_url,
        owner_user_id=owner_user_id,
        row=row,
        history_messages=history_messages,
        prompt=prompt,
        content_parts=content_parts,
    )
    if request.playground_kind == KNOWLEDGE_PLAYGROUND_KIND:
        return _stream_knowledge_playground_message(
            database_url,
            config=config,
            request_id=request_id,
            owner_user_id=owner_user_id,
            owner_role=owner_role,
            session_id=session_id,
            request=request,
        )
    return _stream_chat_request(
        database_url,
        config=config,
        owner_user_id=owner_user_id,
        owner_role=owner_role,
        request_id=request_id,
        request=request,
    )


def send_temporary_playground_message(
    database_url: str,
    *,
    config: AuthConfig,
    request_id: str,
    owner_user_id: int,
    owner_role: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    request = _build_temporary_execution_request(
        database_url=database_url,
        owner_user_id=owner_user_id,
        payload=payload,
    )
    result = _execute_request(
        database_url,
        config=config,
        request_id=request_id,
        owner_user_id=owner_user_id,
        owner_role=owner_role,
        request=request,
    )
    return _serialize_temporary_execution_response(request=request, result=result)


def stream_temporary_playground_message(
    database_url: str,
    *,
    config: AuthConfig,
    request_id: str,
    owner_user_id: int,
    owner_role: str,
    payload: dict[str, Any],
) -> Iterator[dict[str, Any]]:
    request = _build_temporary_execution_request(
        database_url=database_url,
        owner_user_id=owner_user_id,
        payload=payload,
    )
    if request.playground_kind == KNOWLEDGE_PLAYGROUND_KIND:
        return _stream_temporary_knowledge_playground_message(
            database_url,
            config=config,
            request_id=request_id,
            owner_user_id=owner_user_id,
            owner_role=owner_role,
            request=request,
        )
    return _stream_temporary_chat_request(
        database_url,
        config=config,
        request_id=request_id,
        owner_user_id=owner_user_id,
        owner_role=owner_role,
        request=request,
    )


def get_playground_options(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
) -> dict[str, Any]:
    models = get_playground_model_options(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
    )
    knowledge_payload = get_playground_knowledge_base_options(
        database_url,
        config=config,
    )
    return {
        "assistants": PLAYGROUND_ASSISTANTS,
        "models": models["models"],
        "knowledge_bases": knowledge_payload.get("knowledge_bases", []),
        "default_knowledge_base_id": knowledge_payload.get("default_knowledge_base_id"),
        "selection_required": bool(knowledge_payload.get("selection_required", False)),
        "configuration_message": knowledge_payload.get("configuration_message"),
    }


def get_playground_model_options(
    database_url: str,
    *,
    config: AuthConfig,
    actor_user_id: int,
    actor_role: str,
    playground_kind: str | None = None,
) -> dict[str, Any]:
    normalized_playground_kind = _normalize_playground_kind(playground_kind) if playground_kind is not None else None
    accessible_models = list_model_picker_options(
        database_url,
        config=config,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        require_active=True,
        capability_key="llm_inference",
    )
    models = _active_llm_model_options(
        get_active_platform_runtime(database_url, config),
        accessible_models=accessible_models,
    )
    assistants = [
        assistant
        for assistant in PLAYGROUND_ASSISTANTS
        if normalized_playground_kind is None or str(assistant.get("playground_kind", "")).strip().lower() == normalized_playground_kind
    ]
    return {
        "assistants": assistants,
        "models": models,
    }


def _active_llm_model_options(
    platform_runtime: dict[str, Any],
    *,
    accessible_models: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    accessible_by_id = {
        str(model.get("id") or "").strip(): model
        for model in accessible_models
        if str(model.get("id") or "").strip()
    }
    capabilities = platform_runtime.get("capabilities") if isinstance(platform_runtime.get("capabilities"), dict) else {}
    llm_binding = capabilities.get("llm_inference") if isinstance(capabilities.get("llm_inference"), dict) else {}
    resources = llm_binding.get("resources") if isinstance(llm_binding.get("resources"), list) else []
    options: list[dict[str, Any]] = []
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        resource_id = str(resource.get("id") or "").strip()
        if not resource_id or resource_id not in accessible_by_id:
            continue
        accessible_model = accessible_by_id[resource_id]
        options.append(
            {
                "id": resource_id,
                "display_name": str(resource.get("display_name") or accessible_model.get("display_name") or resource_id),
                "task_key": str(accessible_model.get("task_key") or resource.get("task_key") or "llm_inference"),
            }
        )
    return options


def get_playground_knowledge_base_options(
    database_url: str,
    *,
    config: AuthConfig,
) -> dict[str, Any]:
    try:
        knowledge_payload, _status_code = list_knowledge_chat_knowledge_bases(
            database_url=database_url,
            config=config,
        )
        return {
            "knowledge_bases": knowledge_payload.get("knowledge_bases", []),
            "default_knowledge_base_id": knowledge_payload.get("default_knowledge_base_id"),
            "selection_required": bool(knowledge_payload.get("selection_required", False)),
            "configuration_message": knowledge_payload.get("configuration_message"),
        }
    except PlatformControlPlaneError as exc:
        return {
            "knowledge_bases": [],
            "default_knowledge_base_id": None,
            "selection_required": False,
            "configuration_message": exc.message,
        }


def _build_execution_request(
    *,
    database_url: str,
    owner_user_id: int,
    row: dict[str, Any],
    history_messages: list[dict[str, Any]],
    prompt: Any,
    content_parts: Any = None,
) -> PlaygroundExecutionRequest:
    playground_kind = playground_kind_for_conversation_kind(str(row.get("conversation_kind", "")))
    user_content_parts = _normalize_user_content_parts(
        database_url=database_url,
        owner_user_id=owner_user_id,
        prompt=prompt,
        content_parts=content_parts,
    )
    prompt_text = _execution_prompt_for_parts(user_content_parts)
    user_content_text = content_text(user_content_parts, allow_image_parts=True)
    conversation_title = None
    title_source = None
    if not history_messages and str(row.get("title_source") or DEFAULT_TITLE_SOURCE) == DEFAULT_TITLE_SOURCE:
        conversation_title = auto_title_from_prompt(user_content_text or "Image message")
        title_source = DEFAULT_TITLE_SOURCE
    return PlaygroundExecutionRequest(
        playground_kind=playground_kind,
        session_id=str(row.get("id", "")),
        conversation_kind=str(row.get("conversation_kind", "")),
        assistant_ref=string_or_none(row.get("assistant_ref")),
        model_id=string_or_none(row.get("model_id")),
        knowledge_base_id=string_or_none(row.get("knowledge_base_id")),
        prompt=prompt_text,
        user_content_parts=user_content_parts,
        history=[
            {
                "role": str(item.get("role", "")),
                "content": str(item.get("content", "")),
                "content_parts": message_content_parts(item, allow_image_parts=True),
                "metadata": item.get("metadata_json") if isinstance(item.get("metadata_json"), dict) else {},
            }
            for item in history_messages
        ],
        conversation_title=conversation_title,
        title_source=title_source,
    )


def _build_temporary_execution_request(
    *,
    database_url: str,
    owner_user_id: int,
    payload: dict[str, Any],
) -> PlaygroundExecutionRequest:
    playground_kind = _normalize_playground_kind(payload.get("playground_kind"))
    user_content_parts = _normalize_user_content_parts(
        database_url=database_url,
        owner_user_id=owner_user_id,
        prompt=payload.get("prompt"),
        content_parts=payload.get("content_parts"),
    )
    prompt_text = _execution_prompt_for_parts(user_content_parts)
    user_content_text = content_text(user_content_parts, allow_image_parts=True)
    history_messages = _normalize_temporary_history(payload.get("messages"))
    return PlaygroundExecutionRequest(
        playground_kind=playground_kind,
        session_id=string_or_none(payload.get("session_id")) or "temporary",
        conversation_kind=conversation_kind_for_playground_kind(playground_kind),
        assistant_ref=_normalize_assistant_ref(payload.get("assistant_ref"), playground_kind=playground_kind),
        model_id=_normalize_model_id(payload.get("model_selection", payload.get("model_id"))),
        knowledge_base_id=_normalize_knowledge_base_id(payload.get("knowledge_binding", payload.get("knowledge_base_id"))),
        prompt=prompt_text,
        user_content_parts=user_content_parts,
        history=history_messages,
        conversation_title=_temporary_title(payload, user_content_text or "Image message", history_messages),
        title_source=DEFAULT_TITLE_SOURCE,
    )


def _normalize_user_content_parts(
    *,
    database_url: str,
    owner_user_id: int,
    prompt: Any,
    content_parts: Any,
) -> list[dict[str, Any]]:
    parts = _normalize_temporary_content_parts(prompt=prompt, content_parts=content_parts)
    try:
        validate_owned_image_references(database_url, owner_user_id=owner_user_id, parts=parts)
    except ChatAttachmentError as exc:
        raise PlaygroundSessionValidationError(exc.code, exc.message) from exc
    return parts


def _normalize_temporary_content_parts(*, prompt: Any, content_parts: Any) -> list[dict[str, Any]]:
    fallback_text = str(prompt or "").strip()
    parts = normalize_content_parts(content_parts, fallback_text=fallback_text, allow_image_parts=True)
    if not parts:
        raise PlaygroundSessionValidationError("invalid_message_content", "Message text or an image attachment is required")
    return parts


def _execution_prompt_for_parts(parts: list[dict[str, Any]]) -> str:
    text = content_text(parts, allow_image_parts=True)
    if text:
        return normalize_prompt(text)
    return IMAGE_ONLY_EXECUTION_PROMPT


def _normalize_temporary_history(raw_messages: Any) -> list[dict[str, Any]]:
    if raw_messages is None:
        return []
    if not isinstance(raw_messages, list):
        raise PlaygroundSessionValidationError("invalid_messages", "messages must be a list")
    messages: list[dict[str, Any]] = []
    for item in raw_messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        parts = message_content_parts(item, allow_image_parts=True)
        content = content_text(parts, allow_image_parts=True)
        if role not in {"user", "assistant"} or not parts:
            continue
        metadata = item.get("metadata")
        messages.append({
            "role": role,
            "content": content,
            "content_parts": parts,
            "metadata": metadata if isinstance(metadata, dict) else {},
        })
    return messages


def _temporary_title(payload: dict[str, Any], prompt: str, history_messages: Sequence[dict[str, Any]]) -> str:
    raw_title = string_or_none(payload.get("title"))
    if raw_title and raw_title != TEMPORARY_CHAT_TITLE:
        return raw_title
    if history_messages:
        return raw_title or TEMPORARY_CHAT_TITLE
    return auto_title_from_prompt(prompt)


def _execute_request(
    database_url: str,
    *,
    config: AuthConfig,
    request_id: str,
    owner_user_id: int,
    owner_role: str,
    request: PlaygroundExecutionRequest,
) -> PlaygroundExecutionResult:
    if request.playground_kind == CHAT_PLAYGROUND_KIND:
        if str(request.assistant_ref or "").strip().startswith("agent."):
            workflow_run = get_workflow_run(
                database_url,
                owner_user_id=owner_user_id,
                conversation_id=request.session_id,
                assistant_ref=str(request.assistant_ref or ""),
            )
            request.workflow_state = workflow_run.get("workflow_state") if isinstance(workflow_run, dict) else None
            try:
                return execute_agent_chat_request(
                    database_url=database_url,
                    config=config,
                    request_id=request_id,
                    request=request,
                    actor_user_id=owner_user_id,
                    actor_user_role=owner_role,
                )
            except PlatformControlPlaneError as exc:
                raise PlaygroundSessionValidationError(exc.code, exc.message) from exc
        return _execute_chat_request(request)
    if not request.knowledge_base_id:
        raise PlaygroundSessionValidationError(
            "knowledge_base_required",
            "knowledge_binding.knowledge_base_id is required for knowledge playground sessions",
        )
    try:
        return execute_knowledge_request(
            database_url=database_url,
            config=config,
            request_id=request_id,
            request=request,
            actor_user_id=owner_user_id,
            actor_user_role=owner_role,
        )
    except (ModelOpsError, PlatformControlPlaneError) as exc:
        raise PlaygroundSessionValidationError(exc.code, exc.message) from exc


def _is_workflow_assistant(database_url: str, *, assistant_ref: str | None) -> bool:
    normalized = str(assistant_ref or "").strip()
    if not normalized or not normalized.startswith("agent."):
        return False
    try:
        agent = get_catalog_agent(database_url, agent_id=normalized)
    except CatalogError:
        return False
    spec = agent.get("spec") if isinstance(agent.get("spec"), dict) else {}
    return str(spec.get("agent_type") or "").strip().lower() == "workflow"


def _build_assistant_metadata_for_result(
    *,
    request: PlaygroundExecutionRequest,
    result: PlaygroundExecutionResult,
    assistant_parts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    assistant_metadata = {"statuses": result.statuses} if result.statuses else None
    if _has_image_parts(assistant_parts):
        assistant_metadata = dict(assistant_metadata or {})
        assistant_metadata[MESSAGE_CONTENT_METADATA_KEY] = assistant_parts
    if result.workflow_status:
        assistant_metadata = dict(assistant_metadata or {})
        assistant_metadata["workflow_status"] = result.workflow_status
    if request.playground_kind == KNOWLEDGE_PLAYGROUND_KIND:
        assistant_metadata = {
            "response": result.response,
            "sources": result.sources,
            "references": result.references,
            "retrieval": result.retrieval,
            "knowledge_base_id": result.knowledge_base_id,
        }
        if _has_image_parts(assistant_parts):
            assistant_metadata[MESSAGE_CONTENT_METADATA_KEY] = assistant_parts
        if result.statuses:
            assistant_metadata["statuses"] = result.statuses
    return assistant_metadata


def _maybe_bootstrap_workflow_session(
    database_url: str,
    *,
    config: AuthConfig,
    owner_user_id: int,
    owner_role: str,
    session_row: dict[str, Any],
) -> None:
    assistant_ref = string_or_none(session_row.get("assistant_ref"))
    if str(session_row.get("conversation_kind") or "") != "plain":
        return
    if not _is_workflow_assistant(database_url, assistant_ref=assistant_ref):
        return
    request = PlaygroundExecutionRequest(
        playground_kind=CHAT_PLAYGROUND_KIND,
        session_id=str(session_row.get("id") or ""),
        conversation_kind=str(session_row.get("conversation_kind") or "plain"),
        assistant_ref=assistant_ref,
        model_id=string_or_none(session_row.get("model_id")),
        knowledge_base_id=string_or_none(session_row.get("knowledge_base_id")),
        prompt="",
        user_content_parts=[],
        history=[],
        conversation_title=str(session_row.get("title") or DEFAULT_CHAT_TITLE),
        title_source=str(session_row.get("title_source") or DEFAULT_TITLE_SOURCE),
    )
    result = _execute_request(
        database_url,
        config=config,
        request_id=str(uuid4()),
        owner_user_id=owner_user_id,
        owner_role=owner_role,
        request=request,
    )
    assistant_parts = result.content_parts or ([text_part(result.output)] if result.output else [])
    assistant_metadata = _build_assistant_metadata_for_result(
        request=request,
        result=result,
        assistant_parts=assistant_parts,
    )
    persisted = playgrounds_repository.append_messages(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=request.session_id,
        messages=[
            {
                "role": "assistant",
                "content": result.output,
                "metadata": assistant_metadata or {},
            }
        ],
        conversation_title=request.conversation_title,
        title_source=request.title_source,
        conversation_kind=request.conversation_kind,
    )
    if persisted is None:
        raise PlaygroundSessionNotFoundError
    assistant_message = persisted["messages"][0] if persisted.get("messages") else {}
    bind_message_attachments(
        database_url,
        owner_user_id=owner_user_id,
        parts=assistant_parts,
        conversation_id=request.session_id,
        message_id=str(assistant_message.get("id") or ""),
    )
    if request.assistant_ref and result.workflow_state is not None:
        upsert_workflow_run(
            database_url,
            owner_user_id=owner_user_id,
            conversation_id=request.session_id,
            assistant_ref=request.assistant_ref,
            status=result.workflow_status or "running",
            workflow_state=result.workflow_state,
        )


def _execute_chat_request(request: PlaygroundExecutionRequest) -> PlaygroundExecutionResult:
    if not request.model_id:
        raise PlaygroundSessionValidationError("invalid_model_id", "model_selection.model_id is required before sending messages")

    llm_response, status_code = chat_completion_with_allowed_model(
        requested_model_id=request.model_id,
        org_id=None,
        group_id=None,
        messages=build_context_messages(request.history, prompt=request.prompt),
        max_tokens=None,
        temperature=None,
    )
    if llm_response is None:
        raise PlaygroundChatExecutionError(
            {"error": "llm_unreachable", "message": "LLM service unavailable"},
            502,
        )
    if status_code >= 400:
        raise PlaygroundChatExecutionError(
            llm_response if isinstance(llm_response, dict) else {"error": "playground_chat_failed"},
            status_code,
        )

    output = extract_output_text(llm_response)
    if not output:
        raise PlaygroundChatExecutionError(
            {"error": "empty_response", "message": "LLM stream completed without assistant output"},
            502,
        )
    return PlaygroundExecutionResult(
        output=output,
        response=llm_response,
        content_parts=[text_part(output)],
    )


def _persist_execution_result(
    database_url: str,
    *,
    owner_user_id: int,
    request: PlaygroundExecutionRequest,
    result: PlaygroundExecutionResult,
) -> dict[str, Any]:
    user_text = content_text(request.user_content_parts, allow_image_parts=True)
    user_metadata = {MESSAGE_CONTENT_METADATA_KEY: request.user_content_parts}
    assistant_parts = result.content_parts or ([text_part(result.output)] if result.output else [])
    try:
        validate_owned_image_references(database_url, owner_user_id=owner_user_id, parts=assistant_parts)
    except ChatAttachmentError as exc:
        raise PlaygroundSessionValidationError(exc.code, exc.message) from exc
    assistant_metadata = _build_assistant_metadata_for_result(
        request=request,
        result=result,
        assistant_parts=assistant_parts,
    )
    persisted = playgrounds_repository.append_message_pair(
        database_url,
        owner_user_id=owner_user_id,
        conversation_id=request.session_id,
        user_content=user_text,
        assistant_content=result.output,
        user_metadata=user_metadata,
        assistant_metadata=assistant_metadata,
        conversation_title=request.conversation_title,
        title_source=request.title_source,
        conversation_kind=request.conversation_kind,
    )
    if persisted is None:
        raise PlaygroundSessionNotFoundError
    user_message = persisted["messages"][0] if persisted.get("messages") else {}
    assistant_message = persisted["messages"][1] if len(persisted.get("messages") or []) > 1 else {}
    bind_message_attachments(
        database_url,
        owner_user_id=owner_user_id,
        parts=request.user_content_parts,
        conversation_id=request.session_id,
        message_id=str(user_message.get("id") or ""),
    )
    bind_message_attachments(
        database_url,
        owner_user_id=owner_user_id,
        parts=assistant_parts,
        conversation_id=request.session_id,
        message_id=str(assistant_message.get("id") or ""),
    )
    if request.assistant_ref and result.workflow_state is not None:
        upsert_workflow_run(
            database_url,
            owner_user_id=owner_user_id,
            conversation_id=request.session_id,
            assistant_ref=request.assistant_ref,
            status=result.workflow_status or "running",
            workflow_state=result.workflow_state,
        )
    return persisted


def _stream_llm_chat_execution(
    request: PlaygroundExecutionRequest,
    statuses: dict[str, dict[str, Any]],
) -> Generator[dict[str, Any], None, PlaygroundExecutionResult | None]:
    base_details = {"model_id": request.model_id}
    thinking = start_status("thinking", "Thinking", details=base_details)
    yield {"event": "status", "data": _record_status(statuses, thinking)}
    completed_thinking = complete_status(thinking, label="Prepared request")
    yield {"event": "status", "data": _record_status(statuses, completed_thinking)}

    connecting = start_status("connecting", "Preparing model request", details=base_details)
    yield {"event": "status", "data": _record_status(statuses, connecting)}
    stream, error_payload, status_code, provider_telemetry = chat_completion_stream_with_allowed_model(
        requested_model_id=str(request.model_id or ""),
        org_id=None,
        group_id=None,
        messages=build_context_messages(request.history, prompt=request.prompt),
        max_tokens=None,
        temperature=None,
    )
    if error_payload is not None or stream is None:
        yield {
            "event": "error",
            "data": public_stream_error_payload(
                {**error_payload, "status_code": status_code} if isinstance(error_payload, dict) else {"status_code": status_code},
                fallback_error="llm_unreachable",
                fallback_message="LLM service unavailable",
            ),
        }
        return None
    completed_connecting = complete_status(connecting, label="Model request prepared", details={**base_details, **provider_telemetry})
    yield {"event": "status", "data": _record_status(statuses, completed_connecting)}

    def _model_details() -> dict[str, Any]:
        return {"model_id": request.model_id, **provider_telemetry}

    opening = start_status("opening_stream", STREAM_STATUS_LABEL_OPENING, details=_model_details())
    yield {"event": "status", "data": _record_status(statuses, opening)}
    waiting: dict[str, Any] | None = None
    streaming_status: dict[str, Any] | None = None
    assistant_output_parts: list[str] = []
    delta_count = 0

    def _fail_running_generation(label: str) -> dict[str, Any]:
        failed = complete_status(streaming_status or waiting or opening, label=label)
        failed["state"] = "failed"
        return failed

    def _transport_details(event: dict[str, Any] | None = None) -> dict[str, Any]:
        details: dict[str, Any] = _model_details()
        if not event:
            return details
        for key in TRANSPORT_DETAIL_KEYS:
            if event.get(key) is not None:
                details[key] = event.get(key)
        headers = event.get("headers")
        if isinstance(headers, dict) and headers:
            details["headers"] = headers
        return details

    def _transport_summary(event: dict[str, Any] | None = None) -> str | None:
        headers = event.get("headers") if isinstance(event, dict) else None
        if not isinstance(headers, dict):
            return None
        for key in ("x-request-id", "x-openai-request-id", "openai-request-id", "request-id"):
            value = str(headers.get(key) or "").strip()
            if value:
                return f"request id {value}"
        return None

    def _waiting_details(event: dict[str, Any] | None = None) -> dict[str, Any]:
        details = _transport_details(event)
        details["phase"] = STREAM_PHASE_FIRST_TOKEN_DELIVERY
        return details

    for event in stream:
        event_type = str(event.get("type", "")).strip().lower()
        if event_type == "transport":
            if waiting is None:
                completed_opening = complete_status(
                    opening,
                    label=STREAM_STATUS_LABEL_SETUP_COMPLETE,
                    summary=_transport_summary(event),
                    details=_transport_details(event),
                )
                yield {"event": "status", "data": _record_status(statuses, completed_opening)}
                waiting = start_status("waiting_first_token", STREAM_STATUS_LABEL_WAITING_FIRST_TOKEN, details=_waiting_details(event))
                yield {"event": "status", "data": _record_status(statuses, waiting)}
            continue

        if event_type == "delta":
            text = str(event.get("text", ""))
            if not text:
                continue
            if waiting is None:
                completed_opening = complete_status(
                    opening,
                    label=STREAM_STATUS_LABEL_SETUP_COMPLETE,
                    details=_transport_details(),
                )
                yield {"event": "status", "data": _record_status(statuses, completed_opening)}
                waiting = start_status("waiting_first_token", STREAM_STATUS_LABEL_WAITING_FIRST_TOKEN, details=_waiting_details())
                yield {"event": "status", "data": _record_status(statuses, waiting)}
            if streaming_status is None:
                first_token = complete_status(
                    waiting,
                    label=STREAM_STATUS_LABEL_RECEIVED_FIRST_TOKEN,
                    summary="Model started streaming",
                    details=_model_details(),
                )
                yield {"event": "status", "data": _record_status(statuses, first_token)}
                streaming_status = start_status("streaming_tokens", STREAM_STATUS_LABEL_STREAMING, details=_model_details())
                yield {"event": "status", "data": _record_status(statuses, streaming_status)}
            delta_count += 1
            assistant_output_parts.append(text)
            yield {"event": "delta", "data": {"text": text}}
            continue

        if event_type == "error":
            payload = event.get("payload")
            yield {"event": "status", "data": _record_status(statuses, _fail_running_generation("Response generation failed"))}
            yield {
                "event": "error",
                "data": public_stream_error_payload(
                    payload if isinstance(payload, dict) else None,
                    fallback_error="playground_chat_failed",
                    fallback_message="LLM stream failed",
                ),
            }
            return None

        if event_type != "complete":
            continue

        llm_response = event.get("response")
        if not isinstance(llm_response, dict):
            llm_response = {"output": [{"content": [{"type": "text", "text": "".join(assistant_output_parts)}]}]}
        output = extract_output_text(llm_response) or "".join(assistant_output_parts)
        if not output:
            yield {"event": "status", "data": _record_status(statuses, _fail_running_generation("Response generation failed"))}
            yield {
                "event": "error",
                "data": {
                    "error": "empty_response",
                    "message": "LLM stream completed without assistant output",
                },
            }
            return None

        if streaming_status is not None:
            completed_streaming = complete_status(
                streaming_status,
                label=STREAM_STATUS_LABEL_STREAMED,
                summary=f"{len(output)} characters",
                details={**_model_details(), "delta_count": delta_count},
            )
            yield {"event": "status", "data": _record_status(statuses, completed_streaming)}
        else:
            completed_waiting = complete_status(
                waiting or opening,
                label="Received response",
                summary=f"{len(output)} characters",
                details={**_model_details(), "delta_count": 0},
            )
            yield {"event": "status", "data": _record_status(statuses, completed_waiting)}

        return PlaygroundExecutionResult(
            output=output,
            response=llm_response,
            statuses=_status_values(statuses),
            content_parts=[text_part(output)],
        )

    yield {
        "event": "error",
        "data": {
            "error": "stream_incomplete",
            "message": "LLM stream ended before completion",
        },
    }
    return None


def _stream_chat_request(
    database_url: str,
    config: AuthConfig,
    *,
    owner_user_id: int,
    owner_role: str,
    request_id: str,
    request: PlaygroundExecutionRequest,
) -> Iterator[dict[str, Any]]:
    def _stream() -> Iterator[dict[str, Any]]:
        statuses: dict[str, dict[str, Any]] = {}
        if str(request.assistant_ref or "").strip().startswith("agent."):
            workflow_run = get_workflow_run(
                database_url,
                owner_user_id=owner_user_id,
                conversation_id=request.session_id,
                assistant_ref=str(request.assistant_ref or ""),
            )
            request.workflow_state = workflow_run.get("workflow_state") if isinstance(workflow_run, dict) else None
            for event in stream_agent_chat_request(
                database_url=database_url,
                config=config,
                request_id=request_id,
                request=request,
                actor_user_id=owner_user_id,
                actor_user_role=owner_role,
            ):
                event_name = str(event.get("event") or "").strip()
                data = event.get("data")
                if event_name == "status" and isinstance(data, dict):
                    yield {"event": "status", "data": _record_status(statuses, data)}
                    continue
                if event_name == "delta" and isinstance(data, dict):
                    text = str(data.get("text") or "")
                    if text:
                        yield {"event": "delta", "data": {"text": text}}
                    continue
                if event_name == "complete" and isinstance(data, PlaygroundExecutionResult):
                    result = data
                    result.statuses = _status_values(statuses)
                    persisted = _persist_execution_result(
                        database_url,
                        owner_user_id=owner_user_id,
                        request=request,
                        result=result,
                    )
                    session = get_playground_session_detail(
                        database_url,
                        owner_user_id=owner_user_id,
                        session_id=request.session_id,
                        playground_kind=request.playground_kind,
                    )
                    yield {
                        "event": "complete",
                        "data": _serialize_execution_response(
                            session=session,
                            persisted=persisted,
                            result=result,
                        ),
                    }
                    return
            return
        if not request.model_id:
            raise PlaygroundSessionValidationError("invalid_model_id", "model_selection.model_id is required before sending messages")
        result = yield from _stream_llm_chat_execution(request, statuses)
        if result is None:
            return
        result.statuses = _status_values(statuses)
        persisted = _persist_execution_result(
            database_url,
            owner_user_id=owner_user_id,
            request=request,
            result=result,
        )
        session = get_playground_session_detail(
            database_url,
            owner_user_id=owner_user_id,
            session_id=request.session_id,
            playground_kind=request.playground_kind,
        )
        yield {
            "event": "complete",
            "data": _serialize_execution_response(
                session=session,
                persisted=persisted,
                result=result,
            ),
        }
        return

    return _stream()


def _stream_temporary_chat_request(
    database_url: str,
    *,
    config: AuthConfig,
    request_id: str,
    owner_user_id: int,
    owner_role: str,
    request: PlaygroundExecutionRequest,
) -> Iterator[dict[str, Any]]:
    if not request.model_id:
        raise PlaygroundSessionValidationError("invalid_model_id", "model_selection.model_id is required before sending messages")

    def _stream() -> Iterator[dict[str, Any]]:
        statuses: dict[str, dict[str, Any]] = {}
        if str(request.assistant_ref or "").strip().startswith("agent."):
            for event in stream_agent_chat_request(
                database_url=database_url,
                config=config,
                request_id=request_id,
                request=request,
                actor_user_id=owner_user_id,
                actor_user_role=owner_role,
            ):
                event_name = str(event.get("event") or "").strip()
                data = event.get("data")
                if event_name == "status" and isinstance(data, dict):
                    yield {"event": "status", "data": _record_status(statuses, data)}
                    continue
                if event_name == "delta" and isinstance(data, dict):
                    text = str(data.get("text") or "")
                    if text:
                        yield {"event": "delta", "data": {"text": text}}
                    continue
                if event_name == "complete" and isinstance(data, PlaygroundExecutionResult):
                    result = data
                    result.statuses = _status_values(statuses)
                    yield {
                        "event": "complete",
                        "data": _serialize_temporary_execution_response(
                            request=request,
                            result=result,
                        ),
                    }
                    return
            return
        result = yield from _stream_llm_chat_execution(request, statuses)
        if result is None:
            return
        result.statuses = _status_values(statuses)
        yield {
            "event": "complete",
            "data": _serialize_temporary_execution_response(
                request=request,
                result=result,
            ),
        }
        return

    return _stream()


def _serialize_execution_response(
    *,
    session: dict[str, Any],
    persisted: dict[str, Any],
    result: PlaygroundExecutionResult,
) -> dict[str, Any]:
    return {
        "session": session,
        "messages": [serialize_message(message) for message in persisted["messages"]],
        "output": result.output,
        "response": result.response,
        "sources": result.sources,
        "references": result.references,
        "retrieval": result.retrieval,
        "statuses": result.statuses,
    }


def _serialize_temporary_execution_response(
    *,
    request: PlaygroundExecutionRequest,
    result: PlaygroundExecutionResult,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if request.playground_kind == KNOWLEDGE_PLAYGROUND_KIND:
        metadata = {
            "response": result.response,
            "sources": result.sources,
            "references": result.references,
            "retrieval": result.retrieval,
            "knowledge_base_id": result.knowledge_base_id,
        }
    if result.statuses:
        metadata["statuses"] = result.statuses
    user_text = content_text(request.user_content_parts, allow_image_parts=True)
    user_metadata = {MESSAGE_CONTENT_METADATA_KEY: request.user_content_parts}
    assistant_parts = result.content_parts or ([text_part(result.output)] if result.output else [])
    if _has_image_parts(assistant_parts):
        metadata[MESSAGE_CONTENT_METADATA_KEY] = assistant_parts
    messages = [
        *_temporary_history_to_messages(request.history),
        _temporary_message("temporary-user", "user", user_text, metadata=user_metadata),
        _temporary_message("temporary-assistant", "assistant", result.output, metadata=metadata),
    ]
    session = {
        "id": request.session_id,
        "playground_kind": request.playground_kind,
        "assistant_ref": request.assistant_ref or default_assistant_ref_for_kind(request.playground_kind),
        "title": request.conversation_title or TEMPORARY_CHAT_TITLE,
        "title_source": DEFAULT_TITLE_SOURCE,
        "model_selection": {"model_id": request.model_id},
        "knowledge_binding": {"knowledge_base_id": request.knowledge_base_id},
        "message_count": len(messages),
        "created_at": None,
        "updated_at": None,
        "messages": messages,
    }
    return {
        "session": session,
        "messages": messages[-2:],
        "output": result.output,
        "response": result.response,
        "sources": result.sources,
        "references": result.references,
        "retrieval": result.retrieval,
        "statuses": result.statuses,
    }


def _temporary_history_to_messages(history: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for index, item in enumerate(history):
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        parts = item.get("content_parts") if isinstance(item.get("content_parts"), list) else []
        if parts:
            metadata = {**metadata, MESSAGE_CONTENT_METADATA_KEY: parts}
        messages.append(
            _temporary_message(
                f"temporary-history-{index}",
                str(item.get("role") or ""),
                str(item.get("content") or ""),
                metadata=metadata,
            )
        )
    return messages


def _temporary_message(
    message_id: str,
    role: str,
    content: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": message_id,
        "role": role,
        "content": content,
        "content_parts": message_content_parts({"content": content, "metadata": metadata or {}}, allow_image_parts=True),
        "metadata": metadata or {},
        "createdAt": None,
    }


def _stream_knowledge_playground_message(
    database_url: str,
    *,
    config: AuthConfig,
    request_id: str,
    owner_user_id: int,
    owner_role: str,
    session_id: str,
    request: PlaygroundExecutionRequest,
) -> Iterator[dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    for event in stream_knowledge_request(
        database_url=database_url,
        config=config,
        request_id=request_id,
        request=request,
        actor_user_id=owner_user_id,
        actor_user_role=owner_role,
    ):
        event_name = str(event.get("event") or "").strip()
        data = event.get("data")
        if event_name == "status" and isinstance(data, dict):
            yield {"event": "status", "data": _record_status(statuses, data)}
            continue
        if event_name == "delta" and isinstance(data, dict):
            text = str(data.get("text") or "")
            if text:
                yield {"event": "delta", "data": {"text": text}}
            continue
        if event_name != "complete" or not isinstance(data, PlaygroundExecutionResult):
            continue
        result = data
        result.statuses = _status_values(statuses)
        persisted = _persist_execution_result(
            database_url,
            owner_user_id=owner_user_id,
            request=request,
            result=result,
        )
        session = get_playground_session_detail(
            database_url,
            owner_user_id=owner_user_id,
            session_id=session_id,
            playground_kind=request.playground_kind,
        )
        yield {
            "event": "complete",
            "data": _serialize_execution_response(
                session=session,
                persisted=persisted,
                result=result,
            ),
        }
        return


def _stream_temporary_knowledge_playground_message(
    database_url: str,
    *,
    config: AuthConfig,
    request_id: str,
    owner_user_id: int,
    owner_role: str,
    request: PlaygroundExecutionRequest,
) -> Iterator[dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    for event in stream_knowledge_request(
        database_url=database_url,
        config=config,
        request_id=request_id,
        request=request,
        actor_user_id=owner_user_id,
        actor_user_role=owner_role,
    ):
        event_name = str(event.get("event") or "").strip()
        data = event.get("data")
        if event_name == "status" and isinstance(data, dict):
            yield {"event": "status", "data": _record_status(statuses, data)}
            continue
        if event_name == "delta" and isinstance(data, dict):
            text = str(data.get("text") or "")
            if text:
                yield {"event": "delta", "data": {"text": text}}
            continue
        if event_name != "complete" or not isinstance(data, PlaygroundExecutionResult):
            continue
        result = data
        result.statuses = _status_values(statuses)
        yield {
            "event": "complete",
            "data": _serialize_temporary_execution_response(request=request, result=result),
        }
        return


def _require_session(
    database_url: str,
    *,
    owner_user_id: int,
    session_id: str,
) -> dict[str, Any]:
    for conversation_kind in ("plain", "knowledge"):
        row = playgrounds_repository.get_session(
            database_url,
            owner_user_id=owner_user_id,
            conversation_id=session_id,
            conversation_kind=conversation_kind,
        )
        if row is not None:
            return row
    raise PlaygroundSessionNotFoundError


def _load_session_and_messages(
    database_url: str,
    *,
    owner_user_id: int,
    session_id: str,
    playground_kind: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if playground_kind:
        row = playgrounds_repository.get_session(
            database_url,
            owner_user_id=owner_user_id,
            conversation_id=session_id,
            conversation_kind=conversation_kind_for_playground_kind(playground_kind),
        )
        if row is None:
            raise PlaygroundSessionNotFoundError
    else:
        row = _require_session(database_url, owner_user_id=owner_user_id, session_id=session_id)
    messages = playgrounds_repository.list_messages(database_url, conversation_id=session_id)
    return row, messages


def _normalize_session_date(value: str | None, *, field_name: str) -> date | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    if len(normalized) != 10 or normalized[4] != "-" or normalized[7] != "-":
        raise PlaygroundSessionValidationError(
            f"invalid_{field_name}",
            f"{field_name} must use YYYY-MM-DD format",
        )
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise PlaygroundSessionValidationError(
            f"invalid_{field_name}",
            f"{field_name} must use YYYY-MM-DD format",
        ) from exc


def _normalize_session_filters(
    *,
    title_query: str | None,
    updated_from: str | None,
    updated_to: str | None,
) -> dict[str, Any]:
    normalized_from = _normalize_session_date(updated_from, field_name="updated_from")
    normalized_to = _normalize_session_date(updated_to, field_name="updated_to")
    if normalized_from and normalized_to and normalized_from > normalized_to:
        raise PlaygroundSessionValidationError(
            "invalid_updated_range",
            "updated_from must be on or before updated_to",
        )
    return {
        "title_query": str(title_query or "").strip() or None,
        "updated_from": normalized_from,
        "updated_to": normalized_to,
    }


def _serialize_session_summary(row: dict[str, Any]) -> dict[str, Any]:
    playground_kind = playground_kind_for_conversation_kind(str(row.get("conversation_kind", "")))
    return {
        "id": str(row.get("id", "")),
        "playground_kind": playground_kind,
        "assistant_ref": string_or_none(row.get("assistant_ref")) or default_assistant_ref_for_kind(playground_kind),
        "title": str(row.get("title", _default_title_for_kind(playground_kind))),
        "title_source": str(row.get("title_source", DEFAULT_TITLE_SOURCE)),
        "model_selection": {"model_id": string_or_none(row.get("model_id"))},
        "knowledge_binding": {"knowledge_base_id": string_or_none(row.get("knowledge_base_id"))},
        "message_count": int(row.get("message_count") or 0),
        "created_at": serialize_datetime(row.get("created_at")),
        "updated_at": serialize_datetime(row.get("updated_at")),
    }


def _serialize_session_detail(
    row: dict[str, Any],
    messages: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    payload = _serialize_session_summary(row)
    payload["messages"] = [serialize_message(message) for message in messages]
    return payload


def _normalize_playground_kind(value: Any) -> str:
    normalized = str(value or CHAT_PLAYGROUND_KIND).strip().lower() or CHAT_PLAYGROUND_KIND
    if normalized not in {CHAT_PLAYGROUND_KIND, KNOWLEDGE_PLAYGROUND_KIND}:
        raise PlaygroundSessionValidationError("invalid_playground_kind", "playground_kind must be chat or knowledge")
    return normalized


def _normalize_title(value: Any) -> str:
    title = str(value or "").strip()
    if not title:
        raise PlaygroundSessionValidationError("invalid_title", "title is required")
    return title[:120]


def _normalize_assistant_ref(value: Any, *, playground_kind: str) -> str:
    normalized = str(value or "").strip()
    return normalized or default_assistant_ref_for_kind(playground_kind)


def _normalize_model_id(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("model_id")
    normalized = str(value or "").strip()
    return normalized or None


def _normalize_knowledge_base_id(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("knowledge_base_id")
    normalized = str(value or "").strip()
    return normalized or None


def _default_title_for_kind(playground_kind: str) -> str:
    if playground_kind == KNOWLEDGE_PLAYGROUND_KIND:
        return DEFAULT_KNOWLEDGE_TITLE
    return DEFAULT_CHAT_TITLE

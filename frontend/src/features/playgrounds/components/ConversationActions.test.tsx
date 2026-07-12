import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithAppProviders } from "../../../test/renderWithAppProviders";
import ConversationActions from "./ConversationActions";

describe("ConversationActions", () => {
  it("renders a localized reusable action and dispatches its opaque identity", async () => {
    const onAction = vi.fn(async () => undefined);
    const action = {
      id: "action-1",
      type: "start_workflow_cycle",
      label_key: "start_next_loop",
      label: "Fallback label",
      emphasis: "primary",
      state: "enabled",
    };
    await renderWithAppProviders(
      <ConversationActions
        messageId="message-1"
        actions={[action]}
        activeActionKey={null}
        disabled={false}
        onAction={onAction}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Start next loop" }));
    expect(onAction).toHaveBeenCalledWith("message-1", action);
  });

  it("shows consumed and active states without dispatching twice", async () => {
    const onAction = vi.fn(async () => undefined);
    await renderWithAppProviders(
      <ConversationActions
        messageId="message-1"
        actions={[{
          id: "action-1",
          type: "start_workflow_cycle",
          label: "Start next loop",
          emphasis: "primary",
          state: "consumed",
        }]}
        activeActionKey={null}
        disabled={false}
        onAction={onAction}
      />,
    );

    const button = screen.getByRole("button", { name: "Loop started" });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(onAction).not.toHaveBeenCalled();
  });
});

import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { ensureTestI18n, testI18n } from "../test/testI18n";
import {
  ActionFeedbackProvider,
  useActionFeedback,
  useRouteActionFeedback,
  withActionFeedbackState,
} from "./ActionFeedbackProvider";
import { withDeploymentSeedState } from "../features/platform-control/deploymentRouteState";

function TriggerHarness(): JSX.Element {
  const { showErrorFeedback, showSuccessFeedback } = useActionFeedback();
  return (
    <div>
      <button type="button" onClick={() => showErrorFeedback("Embeddings binding is missing a default resource")}>
        Open error
      </button>
      <button type="button" onClick={() => showSuccessFeedback("Validated provider vllm-embeddings-local.")}>
        Open success
      </button>
    </div>
  );
}

function RouteFeedbackHarness(): JSX.Element {
  const location = useLocation();
  useRouteActionFeedback(location.state);
  const deploymentSeed = (location.state as { deploymentSeed?: { display_name?: string } } | null)?.deploymentSeed;
  return (
    <>
      <p>route-ready</p>
      <p>{deploymentSeed?.display_name ?? "no-seed"}</p>
    </>
  );
}

async function renderFeedbackTest(ui: JSX.Element, route = "/", routeState?: unknown): Promise<void> {
  await act(async () => {
    await ensureTestI18n();
    await testI18n.changeLanguage("en");
  });

  render(
    <I18nextProvider i18n={testI18n}>
      <MemoryRouter initialEntries={[{ pathname: route, state: routeState }]}>
        <ActionFeedbackProvider>
          {ui}
        </ActionFeedbackProvider>
      </MemoryRouter>
    </I18nextProvider>,
  );
}

describe("ActionFeedbackProvider", () => {
  it("opens an error modal, supports escape, and closes when dismissed", async () => {
    const user = userEvent.setup();

    await renderFeedbackTest(<TriggerHarness />);

    await user.click(screen.getByRole("button", { name: "Open error" }));

    expect(await screen.findByRole("dialog")).toBeVisible();
    expect(screen.getByText("Embeddings binding is missing a default resource")).toBeVisible();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();

    await user.click(screen.getByRole("button", { name: "Open error" }));
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("opens a success modal and auto-closes it after the default timeout", async () => {
    vi.useFakeTimers();

    await renderFeedbackTest(<TriggerHarness />);

    fireEvent.click(screen.getByRole("button", { name: "Open success" }));

    expect(screen.getByRole("dialog")).toBeVisible();
    expect(screen.getByText("Validated provider vllm-embeddings-local.")).toBeVisible();

    await act(async () => {
      vi.advanceTimersByTime(3200);
    });

    expect(screen.queryByRole("dialog")).toBeNull();
    vi.useRealTimers();
  });

  it("consumes route-state feedback once and does not reopen it on rerender", async () => {
    await renderFeedbackTest(
      <Routes>
        <Route path="/providers" element={<RouteFeedbackHarness />} />
      </Routes>,
      "/providers",
      withDeploymentSeedState(
        {
          id: "deployment-3",
          slug: "staging-profile-copy",
          display_name: "Staging Profile Copy",
          description: "Cloned deployment",
          is_active: false,
          bindings: [],
        },
        withActionFeedbackState({
          kind: "success",
          message: "Assigned a loaded model to vLLM embeddings local and started runtime loading.",
        }),
      ),
    );

    expect(await screen.findByRole("dialog")).toBeVisible();
    expect(screen.getByText("Assigned a loaded model to vLLM embeddings local and started runtime loading.")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByText("route-ready")).toBeVisible();
    expect(screen.getByText("Staging Profile Copy")).toBeVisible();
  });
});

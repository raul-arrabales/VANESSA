import { act, render, type RenderOptions, type RenderResult } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { ThemeProvider } from "../theme/ThemeProvider";
import type { ReactElement } from "react";
import { ensureTestI18n, testI18n } from "./testI18n";
import TestRouter from "./TestRouter";
import { ActionFeedbackProvider } from "../feedback/ActionFeedbackProvider";

type AppRenderOptions = Omit<RenderOptions, "wrapper"> & {
  route?: string;
  routeState?: unknown;
  language?: "en" | "es";
  withTheme?: boolean;
};

export async function renderWithAppProviders(
  ui: ReactElement,
  options: AppRenderOptions = {},
): Promise<RenderResult> {
  const {
    route = "/",
    routeState,
    language = "en",
    withTheme = false,
    ...renderOptions
  } = options;

  window.localStorage.setItem("vanessa.locale", language);
  await act(async () => {
    await ensureTestI18n();
    await testI18n.changeLanguage(language);
  });

  const content = (
    <I18nextProvider i18n={testI18n}>
      <TestRouter route={route} routeState={routeState}>
        <ActionFeedbackProvider>
          {withTheme ? <ThemeProvider>{ui}</ThemeProvider> : ui}
        </ActionFeedbackProvider>
      </TestRouter>
    </I18nextProvider>
  );

  let rendered: RenderResult | null = null;
  await act(async () => {
    rendered = render(content, renderOptions);
    await Promise.resolve();
    await Promise.resolve();
  });

  if (rendered === null) {
    throw new Error("render_failed");
  }

  return rendered;
}

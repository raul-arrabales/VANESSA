import type { ReactNode } from "react";
import { ModelOpsWorkspaceLayout } from "./ModelOpsWorkspaceLayout";

type ModelOpsWorkspaceFrameProps = {
  children: ReactNode;
  secondaryNavigation?: ReactNode;
};

export function ModelOpsWorkspaceFrame({
  children,
  secondaryNavigation,
}: ModelOpsWorkspaceFrameProps): JSX.Element {
  return (
    <ModelOpsWorkspaceLayout secondaryNavigation={secondaryNavigation}>
      {children}
    </ModelOpsWorkspaceLayout>
  );
}

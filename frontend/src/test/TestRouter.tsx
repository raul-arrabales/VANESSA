import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

type TestRouterProps = {
  children: ReactNode;
  route?: string;
};

export default function TestRouter({ children, route = "/" }: TestRouterProps): JSX.Element {
  return (
    <MemoryRouter
      initialEntries={[route]}
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      {children}
    </MemoryRouter>
  );
}

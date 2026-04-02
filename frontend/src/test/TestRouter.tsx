import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

type TestRouterProps = {
  children: ReactNode;
  route?: string;
  routeState?: unknown;
};

export default function TestRouter({ children, route = "/", routeState }: TestRouterProps): JSX.Element {
  const parsedRoute = new URL(route, "http://localhost");

  return (
    <MemoryRouter
      initialEntries={[
        {
          pathname: parsedRoute.pathname,
          search: parsedRoute.search,
          hash: parsedRoute.hash,
          state: routeState,
        },
      ]}
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      {children}
    </MemoryRouter>
  );
}

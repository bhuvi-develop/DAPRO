import { isRouteErrorResponse, useRouteError } from "react-router-dom";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

/** Last-resort error page for a route that failed to render or load (e.g. a chunk failed after a deploy). */
export function RouteError() {
  const err = useRouteError();
  const chunk = err instanceof Error && /dynamically imported module|Loading chunk|Importing a module script failed/i.test(err.message);
  const message = isRouteErrorResponse(err) ? `${err.status} ${err.statusText}` : chunk ? "A newer version of DAPRO is available." : "This page could not be displayed.";
  return (
    <div role="alert" className="flex min-h-screen flex-col items-center justify-center gap-3 bg-background px-6 text-center">
      <div className="rounded-full bg-danger-soft p-3 text-danger"><AlertTriangle className="h-6 w-6" aria-hidden /></div>
      <h1 className="text-lg font-semibold">{message}</h1>
      <p className="max-w-md text-sm text-muted-foreground">Reload the page to continue. If the problem persists, contact your administrator. No data was changed.</p>
      <div className="mt-2 flex gap-2">
        <Button onClick={() => window.location.reload()}><RefreshCw />Reload</Button>
        <Button variant="secondary" onClick={() => window.location.assign("/")}>Go to start</Button>
      </div>
    </div>
  );
}

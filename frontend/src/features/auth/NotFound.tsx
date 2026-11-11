import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { EmptyState } from "@/components/data/states";
import { Button } from "@/components/ui/button";

export function NotFound() {
  return <EmptyState icon={Compass} title="Page not found" description="The page you requested does not exist or has moved." action={<Button asChild variant="secondary"><Link to="/">Back to cockpit</Link></Button>} />;
}

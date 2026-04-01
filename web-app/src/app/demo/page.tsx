import { ResultsView } from "@/components/ResultsView";
import { loadDemoSession } from "@/lib/server-data";

export default async function DemoPage() {
  const session = await loadDemoSession();
  return <ResultsView session={session} />;
}

import { ResultsView } from "@/components/ResultsView";
import { getRenderableSession } from "@/lib/server-data";

export default async function ResultsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const session = await getRenderableSession(id);
  return <ResultsView session={session} />;
}

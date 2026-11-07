import { requireSession } from "@/server/auth/session";
import { Workspace } from "@/app/components/workspace";

export const dynamic = "force-dynamic";

export default async function Home() {
  await requireSession();
  return (
    <Workspace>
      <main className="main">
        <h1>Welcome to AI Factory Demo</h1>
      </main>
    </Workspace>
  );
}


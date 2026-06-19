import { redirect } from "next/navigation";

// DeerFlow JE — redirige directement vers l'interface de chat
export default function RootPage() {
  redirect("/workspace/chats/new");
}

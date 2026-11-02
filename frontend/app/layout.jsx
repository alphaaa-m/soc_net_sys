import "./globals.css";

import { AuthProvider } from "@/components/AuthProvider";
import Nav from "@/components/Nav";

export const metadata = {
  title: "Chirp — text-first social",
  description:
    "A small social network built phase by phase with FastAPI and Next.js.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <div className="shell">
            <Nav />
            <main className="main">{children}</main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}

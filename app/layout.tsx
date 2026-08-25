import type { ReactNode } from "react";

export const metadata = {
  title: "Write Now Publishing House",
  description: "Research and recovery publishing system",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "Georgia, serif", background: "#f7f4ed", color: "#1c1b18" }}>
        {children}
      </body>
    </html>
  );
}

import "./globals.css";
import { Bricolage_Grotesque, IBM_Plex_Sans } from "next/font/google";
import { Nav } from "@/components/Nav";
const display = Bricolage_Grotesque({ subsets: ["latin"], variable: "--font-display" });
const body = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-body" });

export const metadata = { title: "Typhoid: autonomous testing that fixes what it breaks" };
export default function Root({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable}`}>
      <body><Nav />{children}</body>
    </html>
  );
}

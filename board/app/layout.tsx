import type { Metadata } from "next";
import { Lora, Assistant } from "next/font/google";
import "./globals.css";
import { BrandProvider } from "@/lib/brand-context";
import Header from "@/components/Header";

const lora = Lora({
  variable: "--font-lora",
  subsets: ["latin"],
  weight: ["400", "700"],
});

const assistant = Assistant({
  variable: "--font-assistant",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Sportstech — Creative Board",
  description: "Creative asset management for Sportstech",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="de"
      className={`${lora.variable} ${assistant.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <BrandProvider>
          <Header />
          {children}
        </BrandProvider>
      </body>
    </html>
  );
}

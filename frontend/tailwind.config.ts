import type { Config } from "tailwindcss";
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        agar: "#E9EFE4", slide: "#F8FAF5", ink: "#17231F", moss: "#5B6B62",
        culture: "#1E6F5C", colony: "#D98E04", pathogen: "#B3261E", rim: "#CBD6C6",
      },
      fontFamily: { display: ["var(--font-display)", "system-ui"], body: ["var(--font-body)", "system-ui"] },
      borderRadius: { dish: "50%", plate: "6px" },
    },
  },
} satisfies Config;

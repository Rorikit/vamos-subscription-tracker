/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1f2933",
        mint: "#0f8b8d",
        coral: "#f25c54",
      },
      boxShadow: {
        panel: "0 12px 28px rgba(31, 41, 51, 0.08)",
      },
    },
  },
  plugins: [],
};


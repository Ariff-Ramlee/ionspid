module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        se: {
          blue: "rgb(0,128,197)",       // Pantone 285C
          lime: "rgb(181,189,0)",       // Pantone 390C
          gray: "rgb(87,95,101)",       // Pantone Cool Gray 11C
          grayLight: "rgb(230,231,232)",// Soft fallback for backgrounds
          midgray: "rgb(180,187,192)",   // Pantone Cool 2C (website background)
          lightcyan: "rgb(212,239,252)",   // Pantone Cool 2C (website background)
          lightblue: "rgb(109,207,246)",
          darkblue: "rgb(68,149,209)",
          green: "rgb(56,180,73)",
        },
      },
    },
  },
  plugins: [],
};

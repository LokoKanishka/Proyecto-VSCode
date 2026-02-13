/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'void-black': '#050505',
                'cyber-purple': '#b366ff',
                'electric-cyan': '#00f2ff',
            },
            fontFamily: {
                mono: ['Fira Code', 'monospace'],
            },
        },
    },
    plugins: [],
}

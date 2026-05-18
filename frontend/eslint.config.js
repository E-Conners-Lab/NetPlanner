// ESLint flat config (ESLint 9) for the NetPlanner React frontend.
import js from "@eslint/js";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";

export default [
  // Never lint build output or dependencies.
  { ignores: ["dist/**", "node_modules/**"] },

  // Base JavaScript recommended rules.
  js.configs.recommended,

  // Application source — browser React components and hooks.
  {
    files: ["src/**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.browser },
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    settings: {
      react: { version: "18.3" },
    },
    plugins: {
      react,
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...react.configs.recommended.rules,
      // The Vite/React 17+ JSX transform — no `import React` needed.
      ...react.configs["jsx-runtime"].rules,
      ...reactHooks.configs.recommended.rules,
      // Fast Refresh works best when a module only exports components.
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      // PropTypes are not used; this is a JS (not TS) scaffold.
      "react/prop-types": "off",
      // Allow intentionally-unused args/vars prefixed with an underscore.
      "no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
    },
  },

  // Build / tooling config files run under Node, as ES modules.
  {
    files: ["*.config.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.node },
    },
  },
];

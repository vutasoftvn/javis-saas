import js from "@eslint/js";
import nextPlugin from "@next/eslint-plugin-next";
import tseslint from "typescript-eslint";

// eslint-config-next's own FlatCompat wrapper (compat.extends("next/core-web-vitals"))
// crashes on ESLint 9 with the currently pinned eslint-plugin-react /
// @typescript-eslint versions — the FlatCompat legacy validator throws
// "Converting circular structure to JSON" while formatting an unrelated
// warning, because these plugins now embed a self-referential
// `configs.flat.*` on the plugin object itself. Compose native flat
// configs directly instead of going through that broken interop layer.
const eslintConfig = [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    plugins: { "@next/next": nextPlugin },
    rules: {
      ...nextPlugin.configs["core-web-vitals"].rules,
    },
  },
  {
    ignores: [".next/**", "out/**", "node_modules/**"],
  },
];

export default eslintConfig;

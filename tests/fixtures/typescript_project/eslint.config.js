// @ts-check
import eslint from "@eslint/js";

export default [
  eslint.configs.recommended,
  {
    rules: {
      "no-unused-vars": "error",
      "no-console": "warn",
    },
  },
];

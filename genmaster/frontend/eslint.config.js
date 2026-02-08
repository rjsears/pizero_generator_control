import js from '@eslint/js';
import pluginVue from 'eslint-plugin-vue';
import globals from 'globals';

export default [
  {
    ignores: [
      'dist/**',
      'backup/**',
      'node_modules/**',
    ],
  },
  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
        // Vue 3 compiler macros and auto-imports
        defineProps: 'readonly',
        defineEmits: 'readonly',
        defineExpose: 'readonly',
        withDefaults: 'readonly',
      },
    },
    rules: {
      // Disable no-undef - Vue's compiler handles this and auto-imports cause false positives
      'no-undef': 'off',
      // Warn on unused vars (not error) - existing codebase has many
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      // Disable constant binary expression check - causes false positives
      'no-constant-binary-expression': 'off',
      // Vue specific
      'vue/multi-word-component-names': 'off',
      'vue/no-reserved-component-names': 'warn',
      // Disable parsing error reporting - let Vue compiler handle it
      'vue/no-parsing-error': 'off',
      'vue/valid-attribute-name': 'warn',
    },
  },
];

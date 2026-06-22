import tsParser from '@typescript-eslint/parser';
import tseslint from '@typescript-eslint/eslint-plugin';
import importPlugin from 'eslint-plugin-import';
import prettierPlugin from 'eslint-plugin-prettier';
import globals from 'globals';

export default [
	{
		ignores: ['.eslintrc.js', 'test', "eslint.config.js"],
	},
	{
		files: ['**/*.ts'],
		languageOptions: {
			parser: tsParser,
			parserOptions: {
				sourceType: 'module',
				project: './tsconfig.json',
				tsconfigRootDir: import.meta.dirname,
			},
			globals: {
				...globals.node,
				...globals.jest,
			},
		},
		plugins: {
			'@typescript-eslint': tseslint,
			import: importPlugin,
			prettier: prettierPlugin,
		},
		rules: {
			// Prettier
			'prettier/prettier': 'warn',

			// Tipo seguro
			'@typescript-eslint/no-explicit-any': 'warn',
			'@typescript-eslint/explicit-function-return-type': 'off',
			'@typescript-eslint/explicit-module-boundary-types': 'off',

			// Variáveis
			'@typescript-eslint/no-unused-vars': [
				'error',
				{
					args: 'after-used',
					argsIgnorePattern: '^_',
					varsIgnorePattern: '^_',
				},
			],

			// Clean Code / segurança
			'@typescript-eslint/consistent-type-imports': 'error',
			'@typescript-eslint/typedef': [
				'off',
				{
					arrayDestructuring: true,
					arrowParameter: true,
					memberVariableDeclaration: true,
					variableDeclaration: true,
					variableDeclarationIgnoreFunction: false,
				},
			],
			complexity: ['warn', 4],
			'max-lines-per-function': ['warn', 50],
			'max-params': ['warn', 4],
			'no-console': 'warn',
			'no-warning-comments': [
				'warn',
				{ terms: ['todo', 'fixme'], location: 'start' },
			],

			// Importações
			'import/order': [
				'warn',
				{
					groups: [['builtin', 'external', 'internal']],
					'newlines-between': 'always',
					alphabetize: { order: 'asc', caseInsensitive: true },
				},
			],

			// Código seguro
			'@typescript-eslint/no-inferrable-types': 'off',
			'@typescript-eslint/no-empty-function': 'warn',
			'@typescript-eslint/no-misused-promises': 'warn',
			'@typescript-eslint/return-await': 'off',
		},
	},
];


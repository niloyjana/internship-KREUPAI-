module.exports = {
  '*.{ts,tsx,js,jsx}': ['eslint --fix --no-error-on-unmatched-pattern'],
  '*.{ts,tsx,js,jsx,json,md,yml,yaml}': ['prettier --write'],
};

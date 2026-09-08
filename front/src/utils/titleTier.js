const TITLE_TIERS = {
  legendary: new Set([3, 4, 5, 11, 13]),
  rare: new Set([2, 6, 9, 10, 12, 15, 16]),
}

export const getTitleTier = titleId => {
  if (TITLE_TIERS.legendary.has(titleId)) {
    return { key: 'legendary', label: '전설' }
  }
  if (TITLE_TIERS.rare.has(titleId)) {
    return { key: 'rare', label: '희귀' }
  }
  return { key: 'common', label: '일반' }
}

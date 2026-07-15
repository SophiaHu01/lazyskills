// ⚠️ 样式 token:这些值对应 lazycut/assets/style.json(风格资产层)。
// 改风格改那边,这里将来接自动同步——手改本文件会在同步时被覆盖。
// paper/ink/accent/highlight 对应 style.json 的 cards.* 字段。

export const tokens = {
  paper: '#ece2d0',
  ink: '#262019',
  accent: '#c4622d',
  highlight: '#ffd60a',
  font: '"Hiragino Sans GB","PingFang SC","Microsoft YaHei",sans-serif',
} as const;

// 竖屏安全区:1080 宽减两侧 130px(style.json caption.safe_margin_px,平台点赞栏通用值)
export const SAFE_WIDTH = 820;
